"""Real Chromium checks for three globe states, including blocked dependencies.

Unlike static source tests, this catches runtime ReferenceErrors, incorrect
WebGL success claims, and texture-network regressions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview"
PAGE = "http://127.0.0.1:8765/preview/ignis-globe-synthetic.html"


def assert_test(check, message):
    if not check:
        raise AssertionError(message)


def run_case(browser, name, blocked=None):
    page = browser.new_page(viewport={"width": 1480, "height": 890},
                            device_scale_factor=1)
    failures = []
    page.on("pageerror", lambda exc: failures.append(str(exc)))
    if blocked:
        page.route(blocked, lambda route: route.abort())
    page.goto(PAGE, wait_until="domcontentloaded", timeout=30000)
    if name == "blocked-modules":
        page.wait_for_function("window.__ignisGlobeFallbackActive===true", timeout=21000)
        assert_test(page.locator("#ignis-globe-status").inner_text().startswith("WebGL unavailable"),
                    "2D fallback must explicitly identify unavailable WebGL modules")
        assert_test(page.locator("#globe-root canvas").count() > 0,
                    "2D scientific canvas should render if module import fails")
        assert_test(page.locator("text=Retry 3D").count() == 1, "Retry control must exist")
        shot = "ignis-globe-fallback2d.png"
    else:
        page.wait_for_function("window.__ignisGlobeReady===true", timeout=23000)
        assert_test(page.locator("#globe-root canvas").count() > 0,
                    "Three.js should initialize and attach its WebGL canvas")
        assert_test(page.locator("#ignis-speed").is_disabled(),
                    "Current UTC must run at 1x; replay speed selector must be disabled")
        assert_test(page.locator("#ignis-play").is_disabled(),
                    "Current UTC must not allow arbitrary pause/fast forward")
        assert_test(page.locator("#ignis-last-pass").is_disabled(),
                    "No TLE = no calculated last pass event")
        if name == "blocked-textures":
            page.wait_for_function(
                "document.querySelector('#ignis-globe-status').textContent.includes('fallback visuals')",
                timeout=10000)
        else:
            assert_test("Could not initialize" not in page.locator("#globe-root").inner_text(),
                        "No false initialization error on successful WebGL load")
        shot = "ignis-globe-no-textures.png" if name == "blocked-textures" else "ignis-globe-webgl.png"
    assert_test(not failures, f"JavaScript runtime exception: {failures}")
    page.screenshot(path=str(OUT / shot), full_page=False)
    if name != "blocked-modules":
        # A live canvas without any visible planet still fails visual acceptance.
        from PIL import Image
        with Image.open(OUT / shot) as image:
            pixel=image.convert("RGB").getpixel((image.width//2,image.height//2))
        assert_test(pixel[2] > 27 and sum(pixel) > 62,
                    f"Globe visually blank or almost black at center: {pixel}")
    result = {"case": name, "status": "ok", "screenshot": shot,
              "scene_ready": page.evaluate("window.__ignisGlobeReady===true"),
              "fallback_active": page.evaluate("window.__ignisGlobeFallbackActive===true")}
    page.close()
    return result


def main():
    OUT.mkdir(exist_ok=True)
    subprocess.run(["python", str(ROOT / "tests" / "create_globe_browser_fixture.py")], check=True)
    chrome = (shutil.which("google-chrome") or shutil.which("chromium")
              or shutil.which("chromium-browser"))
    assert_test(chrome is not None, "Chrome is required for real browser validation")
    server = subprocess.Popen(
        ["python", "-m", "http.server", "8765", "--bind", "127.0.0.1"],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chrome, headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--enable-webgl", "--enable-unsafe-swiftshader",
                      "--use-angle=swiftshader", "--disable-gpu-sandbox"])
            try:
                results = [
                    run_case(browser, "normal"),
                    run_case(browser, "blocked-textures", "**/textures/planets/**"),
                    run_case(browser, "blocked-modules", "**/node_modules/three/build/three.module.js"),
                ]
            finally:
                browser.close()
        (OUT / "ignis-globe-runtime-results.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(results, indent=2))
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
