"""Optional Chromium integration check using a temporary database and no real accounts.

Install .[dev,browser], install Playwright Chromium or pass --chromium /path/to/chromium.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright
from taxi.manage import create_admin
from taxi.storage import Store

TEST_PASSWORD = "browser-test-password-only"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium")
    parser.add_argument("--screenshots", help="Optional output directory, outside source control")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="taxi-accounts-") as temporary:
        path = Path(temporary) / "taxi.sqlite3"
        create_admin(path, "test-admin", TEST_PASSWORD)
        store = Store(str(path), recover=False)
        for index in range(30):
            store.trip(
                {
                    "id": f"old-trip-{index:02}",
                    "origin": "A",
                    "destination": "B",
                    "status": "COMPLETED",
                }
            )
        store.event("unsafe-text", {"note": '<img src=x onerror="window.injected=true">'})
        store.close()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        api_base = f"http://127.0.0.1:{port}"
        frontend = None
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "taxi.api:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
            env={
                **os.environ,
                "TAXI_DATA_DIR": temporary,
                "TAXI_MODE": "simulation",
                "TAXI_ALLOW_LEGACY_TOKEN": "0",
                "TAXI_SECURE_COOKIES": "0",
            },
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("Test server exited during startup")
                try:
                    urllib.request.urlopen(api_base + "/api/health", timeout=1)
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Test server did not become ready")
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                frontend_port = listener.getsockname()[1]
            base = f"http://127.0.0.1:{frontend_port}"
            frontend = subprocess.Popen(
                ["node", "frontend/server.mjs"],
                cwd=root,
                env={
                    **os.environ,
                    "TAXI_FRONTEND_PORT": str(frontend_port),
                    "TAXI_API_URL": api_base,
                },
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(100):
                if frontend.poll() is not None:
                    raise RuntimeError("Frontend exited during startup")
                try:
                    urllib.request.urlopen(base + "/api/health", timeout=1)
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Frontend/API proxy did not become ready")
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    **({"executable_path": args.chromium} if args.chromium else {}),
                    headless=True,
                    args=["--no-sandbox"],
                )
                errors = []
                admin_context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = admin_context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base + "/admin")
                page.fill("#username", "test-admin")
                page.fill("#password", "incorrect")
                page.click("#sign-in")
                page.wait_for_function(
                    "document.querySelector('#records-feedback').textContent.includes('Invalid username')"
                )
                page.fill("#password", TEST_PASSWORD)
                page.click("#sign-in")
                page.wait_for_function(
                    "document.querySelector('#records-feedback').textContent.includes('Snapshot refreshed')"
                )
                assert "30 matching" in page.locator("#trip-count").inner_text()
                page.click("#trip-next")
                page.wait_for_function(
                    "document.querySelector('#trip-count').textContent.includes('offset 25')"
                )
                page.fill("#trip-search", "old-trip-01")
                page.locator("#trip-filter button").click()
                page.wait_for_function(
                    "document.querySelector('#trip-count').textContent.includes('1 matching')"
                )
                page.locator("#admin-trips summary").click()
                assert "COMPLETED" in page.locator("#admin-trips pre").inner_text()
                page.select_option("#event-kind", "unsafe-text")
                page.locator("#event-filter button").click()
                page.wait_for_function(
                    "document.querySelector('#event-count').textContent.includes('1 matching')"
                )
                page.locator("#admin-events summary").click()
                assert "<img" in page.locator("#admin-events pre").inner_text()
                assert not page.evaluate("Boolean(window.injected)")
                for name, role in [("test-rider", "passenger"), ("test-driver", "operator")]:
                    page.fill("#new-username", name)
                    page.fill("#new-password", TEST_PASSWORD)
                    page.select_option("#new-role", role)
                    page.locator("#new-user-form button").click()
                    page.wait_for_function(
                        f"document.querySelector('#users').textContent.includes('{name}')"
                    )
                rider_context = browser.new_context()
                rider = rider_context.new_page()
                rider.on("pageerror", lambda error: errors.append(str(error)))
                rider.goto(base + "/account")
                rider.fill("#login-username", "test-rider")
                rider.fill("#login-password", TEST_PASSWORD)
                rider.locator("#login-form button").click()
                rider.wait_for_selector("#passenger-panel", state="visible")
                rider.select_option("#destination", "B")
                rider.locator("#booking-form button").click()
                rider.wait_for_selector("#my-trips button")
                assert "ACTIVE" in rider.locator("#my-trips").inner_text()
                rider.locator("#my-trips button").click()
                rider.wait_for_function(
                    "document.querySelector('#my-trips').textContent.includes('CANCELLED')"
                )
                # Admin management/configuration UI uses an explicit version and safe reset gate.
                page.click("#reload-configuration")
                page.wait_for_function(
                    "document.querySelector('#configuration').value.includes('version')"
                )
                page.locator("#configuration-form button").first.click()
                page.wait_for_function(
                    "document.querySelector('#configuration-feedback').textContent.includes('Reset to READY')"
                )
                driver_context = browser.new_context()
                driver = driver_context.new_page()
                driver.on("pageerror", lambda error: errors.append(str(error)))
                driver.goto(base + "/account")
                driver.fill("#login-username", "test-driver")
                driver.fill("#login-password", TEST_PASSWORD)
                driver.locator("#login-form button").click()
                driver.wait_for_function(
                    "document.querySelector('#account-identity').textContent.includes('operator')"
                )
                driver.goto(base + "/operator")
                driver.wait_for_function("document.querySelector('#token').value === ''")
                driver.click("#reset")
                driver.wait_for_function("document.querySelector('#state').textContent === 'READY'")
                page.locator("#configuration").evaluate(
                    "el => { const c=JSON.parse(el.value); c.stops.B='Renamed Library'; el.value=JSON.stringify(c); }"
                )
                page.locator("#configuration-form button").first.click()
                page.wait_for_function(
                    "document.querySelector('#configuration-feedback').textContent.includes('Saved version 1')"
                )
                driver.reload()
                driver.wait_for_function(
                    "document.querySelector('[data-stop=\"B\"]').textContent.includes('Renamed Library')"
                )
                assert "Renamed Library" in driver.locator("#destination").inner_text()
                # Disable the passenger and prove their existing session cannot read trips.
                row = page.locator("#users tr").filter(has_text="test-rider")
                row.locator("input[type=checkbox]").uncheck()
                row.locator("button").click()
                page.wait_for_function(
                    "document.querySelector('#users-feedback').textContent.includes('sessions revoked')"
                )
                rider.click("#refresh-trips")
                rider.wait_for_selector("#login-form", state="visible")
                # Role boundaries apply even when a non-admin opens the admin shell.
                driver.goto(base + "/admin")
                driver.wait_for_function(
                    "document.querySelector('#records-feedback').textContent.includes('does not have administrator')"
                )
                assert not driver.locator("#admin-content").is_visible()
                page.fill("#trip-search", "")
                page.locator("#trip-filter button").click()
                page.wait_for_function(
                    "document.querySelector('#trip-count').textContent.includes('31 matching')"
                )
                if args.screenshots:
                    output = Path(args.screenshots)
                    output.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(output / "admin-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                if args.screenshots:
                    page.screenshot(
                        path=str(Path(args.screenshots) / "admin-mobile.png"), full_page=True
                    )
                # Swagger loads without external services and can execute authenticated mutations.
                swagger_context = browser.new_context()
                swagger = swagger_context.new_page()
                swagger.on("pageerror", lambda error: errors.append(str(error)))
                swagger.route(
                    "**/*",
                    lambda route: (
                        route.continue_()
                        if route.request.url.startswith(base + "/")
                        else route.abort()
                    ),
                )
                swagger.goto(base + "/docs")
                swagger.wait_for_selector(".swagger-ui .opblock")

                def swagger_post(path, body, expected):
                    block = swagger.locator(".opblock.opblock-post").filter(
                        has=swagger.locator(f'.opblock-summary-path[data-path="{path}"]')
                    )
                    block.locator(".opblock-summary").click()
                    block.get_by_role("button", name="Try it out").click()
                    block.locator("textarea.body-param__text").fill(json.dumps(body))
                    with swagger.expect_response(
                        lambda response: (
                            response.url == base + path and response.request.method == "POST"
                        )
                    ) as pending:
                        block.get_by_role("button", name="Execute", exact=True).click()
                    result = pending.value
                    assert result.status == expected, f"Swagger {path}: HTTP {result.status}"
                    return result

                swagger_post(
                    "/api/auth/login", {"username": "test-admin", "password": TEST_PASSWORD}, 200
                )
                created = swagger_post(
                    "/api/admin/users",
                    {"username": "swagger-user", "password": TEST_PASSWORD, "role": "passenger"},
                    201,
                )
                assert created.request.headers.get("x-taxi-csrf")
                assert created.json()["username"] == "swagger-user"
                swagger_context.close()
                page.click("#clear-records")
                page.wait_for_function(
                    "document.querySelector('#records-feedback').textContent === 'Signed out.'"
                )
                page.reload()
                assert not page.locator("#admin-content").is_visible()
                # No logged-in state is presented after a network failure.
                page.route("**/api/auth/login", lambda route: route.abort())
                page.fill("#username", "test-admin")
                page.fill("#password", TEST_PASSWORD)
                page.click("#sign-in")
                page.wait_for_function(
                    "document.querySelector('#records-feedback').textContent.includes('Server unavailable')"
                )
                assert not errors, errors
                browser.close()
                print(
                    "Chromium passed through separate frontend/API processes: admin login/roles, stored reports, server pagination/search, "
                    "text-safe details, user creation/revocation, passenger booking/cancellation, "
                    "operator session controls, configuration gates/save, logout, network error, "
                    "desktop/mobile layout, Swagger login and CSRF-protected Try it out; no JavaScript errors."
                )
        finally:
            if frontend is not None:
                frontend.terminate()
                frontend.wait(timeout=10)
            server.terminate()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
