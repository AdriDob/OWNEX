from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from cores.recon.dedup import (
    SessionDedupTracker,
    dedup_endpoints,
    dedup_naabu_ports,
    dedup_urls,
    fingerprint_endpoint,
    fingerprint_url,
    normalize_url,
)
from cores.recon.naabu_runner import NaabuRunner

# ── URL normalization ────────────────────────────────────────


def test_normalize_url_replaces_uuid():
    url = "https://example.com/api/users/550e8400-e29b-41d4-a716-446655440000/profile"
    assert "{uuid}" in normalize_url(url)


def test_normalize_url_replaces_digits():
    url = "https://example.com/api/users/12345/orders"
    assert "{id}" in normalize_url(url)


def test_normalize_url_replaces_hex():
    url = "https://example.com/file/a1b2c3d4e5f6"
    assert "{hex}" in normalize_url(url) or "{id}" in normalize_url(url)


def test_normalize_url_preserves_static_paths():
    url = "https://example.com/api/health"
    assert normalize_url(url) == url


def test_fingerprint_url_consistent():
    url = "https://example.com/api/users/42/profile"
    fp1 = fingerprint_url(url)
    fp2 = fingerprint_url("https://example.com/api/users/99/profile")
    assert fp1 == fp2


def test_fingerprint_endpoint():
    fp1 = fingerprint_endpoint("/api/users/42", "GET")
    fp2 = fingerprint_endpoint("/api/users/99", "GET")
    fp3 = fingerprint_endpoint("/api/users/42", "POST")
    assert fp1 == fp2
    assert fp1 != fp3


# ── Dedup functions ──────────────────────────────────────────


def test_dedup_urls_removes_duplicates():
    urls = [
        "https://example.com/api/users/1",
        "https://example.com/api/users/2",
        "https://example.com/api/health",
        "https://example.com/api/users/3",
    ]
    result = dedup_urls(urls)
    assert len(result) == 2  # /api/users/* collapses to 1, /api/health stays
    assert "https://example.com/api/health" in result


def test_dedup_urls_empty():
    assert dedup_urls([]) == []


def test_dedup_endpoints():
    eps = [
        {"path": "/api/users/1", "method": "GET"},
        {"path": "/api/users/2", "method": "GET"},
        {"path": "/api/users/1", "method": "POST"},
        {"path": "/api/health", "method": "GET"},
    ]
    result = dedup_endpoints(eps)
    assert len(result) == 3  # /api/users/* GET collapses, POST stays, /api/health stays


def test_dedup_endpoints_default_method():
    eps = [
        {"path": "/api/users/1"},
        {"path": "/api/users/2"},
    ]
    result = dedup_endpoints(eps)
    assert len(result) == 1  # both are GET by default, same normalized path


def test_dedup_naabu_ports():
    ports = [
        {"host": "192.168.1.1", "port": 80},
        {"host": "192.168.1.1", "port": 80},
        {"host": "192.168.1.1", "port": 443},
        {"host": "10.0.0.1", "port": 8080},
    ]
    result = dedup_naabu_ports(ports)
    assert len(result) == 3


def test_dedup_naabu_ports_empty():
    assert dedup_naabu_ports([]) == []


# ── SessionDedupTracker ──────────────────────────────────────


def test_tracker_tracks_urls():
    tracker = SessionDedupTracker()
    assert tracker.is_new_url("https://example.com/api/users/1") is True
    assert tracker.is_new_url("https://example.com/api/users/2") is False  # normalized same
    assert tracker.is_new_url("https://example.com/api/health") is True


def test_tracker_tracks_endpoints():
    tracker = SessionDedupTracker()
    assert tracker.is_new_endpoint("/api/users/1", "GET") is True
    assert tracker.is_new_endpoint("/api/users/2", "GET") is False
    assert tracker.is_new_endpoint("/api/users/1", "POST") is True


def test_tracker_persist(tmp_path):
    persist = tmp_path / "dedup.txt"
    tracker = SessionDedupTracker(persist_path=persist)
    tracker.is_new_url("https://example.com/foo")
    tracker.save()
    assert persist.exists()
    assert len(persist.read_text().splitlines()) > 0


def test_tracker_load(tmp_path):
    persist = tmp_path / "dedup.txt"
    persist.write_text("abc123\n")
    tracker = SessionDedupTracker(persist_path=persist)
    assert "abc123" in tracker._seen_urls


# ── NaabuRunner ──────────────────────────────────────────────


def test_naabu_runner_init(tmp_path):
    runner = NaabuRunner(tmp_path)
    assert runner.output_dir == tmp_path
    assert runner.timeout == 300


def test_naabu_load_open_ports(tmp_path):
    naabu_file = tmp_path / "naabu.json"
    naabu_file.write_text(
        json.dumps({"host": "192.168.1.1", "port": 80, "protocol": "tcp"})
        + "\n"
        + json.dumps({"host": "192.168.1.1", "port": 443, "protocol": "tcp"})
        + "\n"
        + json.dumps({"host": "10.0.0.2", "port": 8080, "protocol": "tcp"})
        + "\n"
    )
    runner = NaabuRunner(tmp_path)
    ports = runner.load_open_ports(naabu_file)
    assert len(ports) == 3
    assert ports[0]["host"] == "192.168.1.1"
    assert ports[0]["port"] == 80


def test_naabu_load_open_ports_empty(tmp_path):
    runner = NaabuRunner(tmp_path)
    missing = tmp_path / "nonexistent.json"
    assert runner.load_open_ports(missing) == []


def test_naabu_load_open_ports_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json\nstill not json\n")
    runner = NaabuRunner(tmp_path)
    ports = runner.load_open_ports(f)
    assert ports == []


def test_naabu_as_httpx_targets():
    runner = NaabuRunner(Path("/tmp"))
    ports = [
        {"host": "10.0.0.1", "port": 80},
        {"host": "10.0.0.1", "port": 443},
        {"host": "10.0.0.1", "port": 8080},
        {"host": "10.0.0.2", "port": 443},
    ]
    targets = runner.as_httpx_targets(ports)
    assert "http://10.0.0.1" in targets  # port 80
    assert "https://10.0.0.1" in targets  # port 443
    assert "http://10.0.0.1:8080" in targets  # port 8080
    assert "https://10.0.0.2" in targets  # port 443 second host


def test_naabu_as_httpx_targets_dedup():
    runner = NaabuRunner(Path("/tmp"))
    ports = [
        {"host": "10.0.0.1", "port": 80},
        {"host": "10.0.0.1", "port": 80},
        {"host": "10.0.0.1", "port": 443},
    ]
    targets = runner.as_httpx_targets(ports)
    assert len(targets) == 2  # 80 + 443 only once each
    assert "http://10.0.0.1" in targets
    assert "https://10.0.0.1" in targets


# ── ReconRunner with Naabu ───────────────────────────────────


@patch("cores.recon.runner.SubfinderRunner")
@patch("cores.recon.runner.NaabuRunner")
@patch("cores.recon.runner.HttpxRunner")
@patch("cores.recon.runner.KatanaRunner")
@patch("cores.recon.runner.NucleiRunner")
@patch("cores.recon.runner.CrtshRunner")
@patch("cores.recon.runner.WhoisRunner")
@patch("cores.recon.runner.WaybackRunner")
@patch("cores.recon.runner.GauRunner")
@patch("cores.recon.runner.FfufRunner")
def test_recon_runner_init(
    mock_ffuf,
    mock_gau,
    mock_wayback,
    mock_whois,
    mock_crtsh,
    mock_nuclei,
    mock_katana,
    mock_httpx,
    mock_naabu,
    mock_subfinder,
):
    from cores.recon.runner import ReconRunner

    runner = ReconRunner(Path("/tmp/test_target"))
    assert runner.naabu is not None
    assert runner.httpx is not None
    assert runner.subfinder is not None
