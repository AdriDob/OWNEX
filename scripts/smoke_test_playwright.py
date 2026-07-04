#!/usr/bin/env python3
"""CATEYE Playwright Smoke Test — validates frontend JS execution in a headless browser.

Detects JavaScript runtime errors (e.g. "No QueryClient set") that HTTP-only
smoke tests cannot catch, because they never execute JS.

Usage:
    python scripts/smoke_test_playwright.py                        # Uses dist/CATEYE/CATEYE.exe
    python scripts/smoke_test_playwright.py --exe path/to/CATEYE.exe
    python scripts/smoke_test_playwright.py --install-playwright   # Auto-install playwright + chromium

Requires:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PASS = 0
FAIL = 0
SKIP = 0
TIMESTAMP = time.strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"  {msg}")


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"  \u2713 {msg}")


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  \u2717 {msg}")


def skip(msg: str) -> None:
    global SKIP
    SKIP += 1
    print(f"  \u2014 {msg}")


def http_get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 0, str(e)


def wait_for_health(url: str, timeout: float = 30.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        status, body = http_get(url, timeout=2.0)
        if status == 200:
            return True
        time.sleep(0.5)
    return False


def install_playwright() -> bool:
    log("Installing playwright package...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "playwright", "--quiet"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        log(f"  pip install failed: {result.stderr[-200:]}")
        return False
    log("  playwright package installed")

    log("Installing Chromium browser...")
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        log(f"  playwright install chromium failed: {result.stderr[-200:]}")
        return False
    log("  Chromium installed")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="CATEYE Playwright Smoke Test")
    parser.add_argument("--exe", type=Path, default=None, help="Path to CATEYE.exe")
    parser.add_argument("--host", default="127.0.0.1", help="Backend host")
    parser.add_argument("--port", type=int, default=8000, help="Backend port")
    parser.add_argument("--ci", action="store_true", help="CI mode")
    parser.add_argument("--install-playwright", action="store_true", help="Install playwright + chromium")
    args = parser.parse_args()

    if args.exe:
        exe_path = args.exe.resolve()
    else:
        exe_path = Path(__file__).resolve().parent.parent / "dist" / "CATEYE" / "CATEYE.exe"

    if not exe_path.exists():
        print(f"\n\u2717 CATEYE.exe not found at: {exe_path}")
        print("  Build first: pyinstaller CATEYE.spec -y")
        sys.exit(1)

    host = args.host
    port = args.port
    base_url = f"http://{host}:{port}"
    health_url = f"{base_url}/api/health"

    print(f"\n{'=' * 60}")
    print("  CATEYE PLAYWRIGHT SMOKE TEST")
    print(f"  {TIMESTAMP}")
    print(f"  Executable: {exe_path}")
    print(f"{'=' * 60}\n")

    # ── Ensure Playwright is available ─────────────────────────────
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if args.install_playwright:
            log("Playwright not found, attempting install...")
            if not install_playwright():
                fail("Failed to install playwright")
                sys.exit(1)
            from playwright.sync_api import sync_playwright
        else:
            log("Playwright not installed.")
            log("  Install with:  pip install playwright && playwright install chromium")
            log("  Or rerun with: --install-playwright")
            skip("Playwright smoke test skipped (playwright not available)")
            print(f"\n{'=' * 60}")
            print(f"  RESULTS:  {PASS} passed, {FAIL} failed, {SKIP} skipped")
            print(f"{'=' * 60}\n")
            sys.exit(0)

    # ── 1. Start the backend ───────────────────────────────────────
    log("Starting CATEYE.exe --browser --no-tray ...")
    env = os.environ.copy()
    env["CATEYE_DESKTOP"] = "1"
    env["CATEYE_SMOKE_TEST"] = "1"

    proc = subprocess.Popen(
        [str(exe_path), "--browser", "--no-tray"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    # ── 2. Wait for backend to be healthy ───────────────────────────
    log("Waiting for backend (up to 30s)...")
    healthy = wait_for_health(health_url, timeout=30.0)
    if healthy:
        ok("Backend started and healthy")
    else:
        fail("Backend failed to start (health endpoint timeout)")
        proc.kill()
        sys.exit(1)

    # ── 3. Open Playwright browser and collect console messages ────
    log("Opening headless Chromium via Playwright...")
    console_errors: list[str] = []
    page_errors: list[str] = []
    navigated = False
    screenshot_path = exe_path.parent / "playwright_failure.png"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
            )
            page = context.new_page()

            # Collect all console messages
            page.on("console", lambda msg: console_errors.append(
                f"[{msg.type}] {msg.text}"
            ))

            # Collect page errors (uncaught exceptions)
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            log(f"Navigating to {base_url}/ ...")
            try:
                page.goto(f"{base_url}/", timeout=30000, wait_until="networkidle")
                navigated = True
                ok("Page loaded successfully")
            except Exception as e:
                fail(f"Page load failed: {e}")
                page.screenshot(path=str(screenshot_path))
                log(f"  Screenshot saved: {screenshot_path}")

            # Wait a moment for any async JS errors
            page.wait_for_timeout(2000)

            # ── 4. Check page content ───────────────────────────────
            if navigated:
                title = page.title()
                log(f"  Page title: {title}")

                # Check for React root rendering
                root_content = page.content()
                has_react_root = 'id="root"' in root_content or '__reactFiber' in root_content
                if has_react_root:
                    ok("React root found in DOM")
                else:
                    fail("React root not found — app may not have mounted")

                # Check body has content (not blank)
                body_text = page.evaluate("document.body?.innerText || ''")
                if body_text.strip():
                    ok(f"Page body has content ({len(body_text.strip())} chars)")
                else:
                    fail("Page body is empty — app may have crashed before render")

            # ── 5. Analyze console messages for errors ──────────────
            # Fatal JS errors — real bugs (React crash, QueryClient, TypeError, etc.)
            fatal_patterns = [
                "No QueryClient set",
                "Uncaught",
                "Unhandled",
                "React has encountered an error",
                "Cannot read properties of undefined",
                "Cannot read properties of null",
                "Minified React error",
                "TypeError",
                "ReferenceError",
                "SyntaxError",
            ]

            # HTTP 401/403 are expected during boot (auth checks, no token yet)
            expected_boot_errors = [
                msg for msg in console_errors
                if msg.startswith("[error]") and ("401" in msg or "403" in msg)
            ]
            # Real JS errors — everything except expected HTTP 401/403
            js_errors = [
                msg for msg in console_errors
                if msg.startswith("[error]") or msg.startswith("[assert]")
            ]
            real_js_errors = [
                msg for msg in js_errors
                if msg not in expected_boot_errors
            ]
            fatal_errors = [
                msg for msg in console_errors
                if any(p in msg for p in fatal_patterns)
            ]
            warnings = [
                msg for msg in console_errors
                if msg.startswith("[warning]")
            ]

            if expected_boot_errors:
                for err in expected_boot_errors:
                    log(f"  [expected boot] {err[:200]}")
                log(f"  ({len(expected_boot_errors)} HTTP 401/403 — expected during boot)")

            if real_js_errors:
                for err in real_js_errors:
                    fail(f"Console error: {err[:200]}")
            else:
                ok("No console errors (HTTP 401/403 boot noise excluded)")

            if fatal_errors:
                for err in fatal_errors:
                    fail(f"Fatal JS error: {err[:200]}")
                if not navigated:
                    page.screenshot(path=str(screenshot_path))
                    log(f"  Screenshot saved: {screenshot_path}")
            else:
                ok("No fatal JS errors (No QueryClient set, React crash, etc.)")

            if warnings:
                for w in warnings:
                    log(f"  [warn] {w[:200]}")

            if page_errors:
                for err in page_errors:
                    fail(f"Page error: {err[:200]}")
            else:
                ok("No page-level uncaught exceptions")

            # ── 6. Report summary ──────────────────────────────────
            non_fatal = len(console_errors) - len(real_js_errors) - len(fatal_errors) - len(expected_boot_errors)
            log(f"\n  Console messages: {len(console_errors)} total "
                f"({len(real_js_errors)} errors, {len(fatal_errors)} fatal, "
                f"{len(expected_boot_errors)} HTTP 401/403 boot noise, "
                f"{len(warnings)} warnings, {non_fatal} info/debug)")

            browser.close()

    except Exception as e:
        fail(f"Playwright test exception: {e}")
        if args.ci:
            raise

    # ── 7. Clean shutdown ─────────────────────────────────────────
    log("\nShutting down CATEYE...")
    proc.terminate()
    try:
        proc.wait(timeout=10.0)
        ok(f"Clean shutdown (exit code {proc.returncode})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        fail("Forced kill (did not shutdown cleanly in 10s)")

    # ── Results ─────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  RESULTS:  {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'=' * 60}\n")

    if FAIL > 0:
        print("  BUILD FAILED — Playwright smoke test errors detected")
        sys.exit(1)

    print("  Playwright smoke test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
