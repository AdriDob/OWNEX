
from fastapi import APIRouter, HTTPException, Query

from cores.confidence import audit_findings, audit_single, audit_verdicts
from cores.replay import build_replay, list_replay_targets
from cores.review_queue import build_review_queue
from cores.timeline import build_timeline

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/timeline")
def get_timeline(
    target_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: str | None = Query(None),
):
    timeline = build_timeline(
        target_id=target_id,
        limit=limit,
        offset=offset,
        event_type=event_type,
    )
    return timeline.to_dict()


@router.get("/replay")
def get_replay_list():
    targets = list_replay_targets()
    return {"targets": targets, "total": len(targets)}


@router.get("/definitions")
def get_definitions():
    """Return system definitions: platforms, tools, OSINT services — consumed by frontend Settings, Connections, Identity."""
    return {
        "platforms": [
            {"id": "hackerone", "name": "HackerOne", "color": "#00d46a", "url": "https://hackerone.com"},
            {"id": "bugcrowd", "name": "Bugcrowd", "color": "#f56e2f", "url": "https://bugcrowd.com"},
            {"id": "intigriti", "name": "Intigriti", "color": "#6935d3", "url": "https://intigriti.com"},
            {"id": "synack", "name": "Synack", "color": "#1e88e5", "url": "https://synack.com"},
            {"id": "yeswehack", "name": "YesWeHack", "color": "#ff6b6b", "url": "https://yeswehack.com"},
            {"id": "immunefi", "name": "Immunefi", "color": "#8b5cf6", "url": "https://immunefi.com"},
            {"id": "code4rena", "name": "Code4rena", "color": "#e11d48", "url": "https://code4rena.com"},
        ],
        "tools": [
            {"id": "nuclei", "name": "Nuclei", "desc": "Template-based scanner"},
            {"id": "amass", "name": "Amass", "desc": "Subdomain enumeration"},
            {"id": "subfinder", "name": "Subfinder", "desc": "Passive subdomain discovery"},
            {"id": "httpx", "name": "Httpx", "desc": "HTTP probe & analysis"},
            {"id": "katana", "name": "Katana", "desc": "Crawler & spider"},
            {"id": "ffuf", "name": "Ffuf", "desc": "Fuzzing framework"},
            {"id": "gau", "name": "Gau", "desc": "URL gathering"},
            {"id": "naabu", "name": "Naabu", "desc": "Port scanner"},
            {"id": "assetfinder", "name": "Assetfinder", "desc": "Asset discovery"},
            {"id": "dnsx", "name": "Dnsx", "desc": "DNS resolver"},
        ],
        "osint_services": [
            {"id": "shodan", "name": "Shodan", "free": True, "url": "https://account.shodan.io"},
            {"id": "censys", "name": "Censys", "free": True, "url": "https://search.censys.io/account/api"},
            {"id": "virustotal", "name": "VirusTotal", "free": True, "url": "https://virustotal.com/gui/my-apikey"},
            {"id": "securitytrails", "name": "SecurityTrails", "free": False, "url": "https://securitytrails.com/app/account/credentials"},
            {"id": "alienvault", "name": "AlienVault OTX", "free": True, "url": "https://otx.alienvault.com/settings"},
            {"id": "urlscan", "name": "URLScan.io", "free": True, "url": "https://urlscan.io/user/api/"},
            {"id": "hunter", "name": "Hunter.io", "free": True, "url": "https://hunter.io/api-keys"},
            {"id": "builtwith", "name": "BuiltWith", "free": False, "url": "https://api.builtwith.com/register"},
            {"id": "hibp", "name": "Have I Been Pwned", "free": False, "url": "https://haveibeenpwned.com/API/Key"},
            {"id": "greynoise", "name": "GreyNoise", "free": True, "url": "https://www.greynoise.io/account"},
            {"id": "intelx", "name": "Intelligence X", "free": False, "url": "https://intelx.io/account"},
            {"id": "pulsedive", "name": "Pulsedive", "free": True, "url": "https://pulsedive.com/account/"},
            {"id": "ipinfo", "name": "IPInfo", "free": True, "url": "https://ipinfo.io/account"},
        ],
        "languages": [{"id": "es", "name": "Español"}, {"id": "en", "name": "English"}, {"id": "pt", "name": "Português"}],
        "event_types": ["scan", "finding", "report", "verdict", "sync", "system"],
    }


@router.get("/replay/{target_id}")
def get_replay(target_id: int):
    try:
        replay = build_replay(target_id)
        return replay.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/confidence")
def get_confidence_audit(
    item_type: str = Query("verdict"),
    limit: int = Query(50, ge=1, le=200),
):
    report = audit_verdicts(limit=limit) if item_type == "verdict" else audit_findings(limit=limit)
    return report.to_dict()


@router.get("/confidence/{item_type}/{item_id}")
def get_confidence_single(item_type: str, item_id: int):
    if item_type not in ("verdict", "finding"):
        raise HTTPException(status_code=400, detail="item_type must be 'verdict' or 'finding'")
    audit = audit_single(item_type, item_id)
    if audit is None:
        raise HTTPException(status_code=404, detail=f"{item_type} {item_id} not found")
    return audit.to_dict()


@router.get("/review")
def get_review_queue(limit: int = Query(100, ge=1, le=500)):
    queue = build_review_queue(limit=limit)
    return queue.to_dict()


@router.get("/state")
def get_system_state():
    """Full system state summary with service health details."""
    from cores.system_state import get_system_state as _get_state
    state = _get_state()
    return {
        "state": state.get_summary(),
        "services": state.get_services(),
    }


@router.get("/state/events")
def get_system_state_events(
    event_type: str = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=200),
):
    """Recent event bus history."""
    from cores.events.event_bus import get_event_bus
    bus = get_event_bus()
    events = bus.get_history(event_type=event_type, limit=limit)
    return {
        "events": events,
        "total": len(events),
    }


@router.get("/update-check")
def check_update():
    from desktop.updater import _current_version, check_for_updates
    release = check_for_updates()
    if release is None:
        return {"available": False, "current_version": _current_version()}
    return {
        "available": True,
        "version": release.version,
        "download_url": release.download_url,
        "release_notes_url": release.release_notes_url,
        "current_version": _current_version(),
    }
