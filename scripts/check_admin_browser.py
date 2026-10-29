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
    parser.add_argument("--axe", help="Optional path to axe.min.js for accessibility audits")
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

                def review_interface(target, name):
                    for width in (1440, 768, 390, 360):
                        target.set_viewport_size(
                            {"width": width, "height": 1000 if width > 768 else 844}
                        )
                        assert target.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        ), (name, width)
                        palette = target.evaluate("""() => {
                            const css=getComputedStyle(document.documentElement);
                            return ['--bg','--surface','--primary','--highlight','--text','--muted'].map(k=>css.getPropertyValue(k).trim().toUpperCase());
                        }""")
                        assert palette == [
                            "#080D0A",
                            "#122019",
                            "#22C55E",
                            "#FACC15",
                            "#F5F7F5",
                            "#A7B5AC",
                        ]
                        target.evaluate("document.activeElement?.blur();scrollTo(0,0)")
                        if args.screenshots and width in (1440, 390):
                            output = Path(args.screenshots)
                            output.mkdir(parents=True, exist_ok=True)
                            target.screenshot(
                                path=str(output / f"{name}-{width}.png"), full_page=True
                            )
                            target.screenshot(path=str(output / f"{name}-{width}-viewport.png"))
                        if args.axe and width in (1440, 390):
                            target.add_script_tag(path=args.axe)
                            violations = target.evaluate("""async () => (await axe.run(document, {
                                runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}
                            })).violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))""")
                            assert not violations, (name, width, violations)
                    target.set_viewport_size({"width": 1440, "height": 1000})
                    target.evaluate("scrollTo(0,0)")
                    target.keyboard.press("Tab")
                    target.locator(".skip-link").focus()
                    assert target.locator(".skip-link").evaluate(
                        "el => getComputedStyle(el).outlineStyle !== 'none'"
                    )
                    target.keyboard.press("Enter")
                    assert target.locator("#main").evaluate("el => document.activeElement === el")

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
                for name, role in [
                    ("test-rider", "passenger"),
                    ("test-driver", "operator"),
                    ("ui-rider", "passenger"),
                ]:
                    page.uncheck("#new-force-password")
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
                rider.goto(base + "/passenger")
                rider.check('input[name="destination"][value="B"]')
                rider.click("#book-trip")
                rider.wait_for_selector("#cancel-trip", state="visible")
                assert "Active" in rider.locator("#trip-badge").inner_text()
                rider.click("#cancel-trip")
                rider.wait_for_function(
                    "document.querySelector('#trip-badge').textContent.includes('CANCELLED')"
                )
                review_interface(rider, "passenger")
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
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'READY'"
                )
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
                rider.click("#refresh-passenger")
                rider.wait_for_function(
                    "document.querySelector('#passenger-access').textContent.includes('session expired')"
                )
                assert rider.locator("#book-trip").is_disabled()
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
                # A second passenger completes a real simulated trip; progress belongs to that ID.
                ui_context = browser.new_context()
                ui_rider = ui_context.new_page()
                ui_rider.on("pageerror", lambda error: errors.append(str(error)))
                ui_rider.goto(base + "/account")
                ui_rider.fill("#login-username", "ui-rider")
                ui_rider.fill("#login-password", TEST_PASSWORD)
                ui_rider.locator("#login-form button").click()
                ui_rider.wait_for_selector("#account-next", state="visible")
                review_interface(ui_rider, "account")
                ui_rider.goto(base + "/passenger")
                ui_rider.check('input[name="destination"][value="B"]')
                ui_rider.click("#book-trip")
                ui_rider.wait_for_selector("#cancel-trip", state="visible")
                ui_rider.wait_for_function(
                    "document.querySelector('#trip-progress').value === 100", timeout=25000
                )
                assert "Arrival confirmed" in ui_rider.locator("#progress-copy").inner_text()
                assert "COMPLETED" in ui_rider.locator("#trip-badge").inner_text()
                assert ui_rider.locator("#cancel-trip").is_hidden()
                review_interface(ui_rider, "passenger-arrived")
                # Passenger credentials never enable the operator UI.
                ui_rider.goto(base + "/operator")
                ui_rider.wait_for_function(
                    "document.querySelector('#access-note').textContent.includes('passenger account')"
                )
                assert ui_rider.locator("#start").is_disabled()
                assert ui_rider.locator("#stop").is_disabled()
                # Capture a real fault, then withhold WebSocket messages to prove stale/disconnect behavior.
                transport = {"freeze": False, "client": None}

                def bridge(client):
                    transport["client"] = client
                    upstream = client.connect_to_server()
                    upstream.on_message(
                        lambda message: None if transport["freeze"] else client.send(message)
                    )

                driver.route_web_socket("**/ws/telemetry", bridge)
                driver.goto(base + "/operator")
                driver.click("#reset")
                driver.select_option("#destination", "B")
                driver.click("#start")
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'ACTIVE'"
                )
                driver.check("#obstacle")
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'FAULT'"
                )
                driver.uncheck("#obstacle")
                driver.wait_for_function("!document.querySelector('#rearm').disabled")
                review_interface(driver, "operator-fault")
                transport["freeze"] = True
                driver.wait_for_function(
                    "document.querySelector('#connection').textContent.includes('Stale')"
                )
                for control in (
                    "#start",
                    "#rearm",
                    "#reset",
                    "#obstacle",
                    "#sensor_failed",
                    "#link_failed",
                ):
                    assert driver.locator(control).is_disabled(), control
                assert not driver.locator("#stop").is_disabled()
                assert driver.locator("#speed").inner_text() == "Unavailable"
                assert driver.locator("#route-map").get_attribute("data-stale") == "true"
                review_interface(driver, "operator-stale")
                transport["client"].send("not valid telemetry")
                driver.wait_for_function(
                    "document.querySelector('#connection').textContent.includes('Invalid')"
                )
                assert driver.locator("#start").is_disabled()
                transport["client"].close(code=1000)
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'DISCONNECTED'"
                )
                assert driver.locator("#start").is_disabled()
                transport["freeze"] = False
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'FAULT'"
                )
                assert driver.locator("#start").is_disabled()  # Reconnect did not rearm the fault.
                diagnostic = browser.new_page()
                diagnostic.on("pageerror", lambda error: errors.append(str(error)))
                diagnostic.goto(base + "/diagnostics")
                diagnostic.wait_for_function(
                    "document.querySelector('#diagnostic-source').textContent === 'Simulated'"
                )
                assert "Unavailable" in diagnostic.locator(".diagnostic-list").last.inner_text()
                assert "Fault" in diagnostic.locator("#diag-vehicle").inner_text()
                review_interface(diagnostic, "diagnostics")
                driver.check("#sensor_failed")
                diagnostic.wait_for_function(
                    "document.querySelector('#sensor-validity').textContent.includes('Invalid')"
                )
                assert "Unavailable" in diagnostic.locator(".diagnostic-list").last.inner_text()
                driver.uncheck("#sensor_failed")
                driver.click("#reset")
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'READY'"
                )
                review_interface(driver, "operator-ready")
                driver.set_viewport_size({"width": 390, "height": 844})
                driver.select_option("#destination", "B")
                driver.click("#start")
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'ACTIVE'"
                )
                driver.click("#stop-phone")
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'STOPPED'"
                )
                assert driver.locator("#stop").is_hidden()
                assert driver.locator("#stop-phone").is_visible()
                driver.click("#reset")
                driver.wait_for_function(
                    "document.querySelector('#state').dataset.code === 'READY'"
                )
                # Passenger progress and booking become unavailable when messages stop arriving.
                passenger_transport = {"freeze": False, "client": None}

                def passenger_bridge(client):
                    passenger_transport["client"] = client
                    upstream = client.connect_to_server()
                    upstream.on_message(
                        lambda message: (
                            None if passenger_transport["freeze"] else client.send(message)
                        )
                    )

                ui_rider.route_web_socket("**/ws/telemetry", passenger_bridge)
                ui_rider.goto(base + "/passenger")
                ui_rider.wait_for_function("!document.querySelector('#book-trip').disabled")
                passenger_transport["freeze"] = True
                ui_rider.wait_for_function(
                    "document.querySelector('#connection').textContent.includes('Stale')"
                )
                assert ui_rider.locator("#book-trip").is_disabled()
                assert ui_rider.locator("#passenger-speed").inner_text() == "Unavailable"
                assert ui_rider.locator("#trip-progress").evaluate("el => el.value") == 0
                review_interface(ui_rider, "passenger-stale")
                passenger_transport["client"].close(code=1000)
                ui_rider.wait_for_function(
                    "document.querySelector('#connection').textContent.includes('Disconnected')"
                )
                passenger_transport["freeze"] = False
                ui_rider.wait_for_function("!document.querySelector('#book-trip').disabled")
                # Shared native validation exposes an explicit inline error and invalid field state.
                page.fill("#new-username", "bad name")
                page.fill("#new-password", TEST_PASSWORD)
                page.locator("#new-user-form button").click()
                assert page.locator("#new-username").get_attribute("aria-invalid") == "true"
                assert page.locator("#users-feedback").get_attribute("role") == "alert"
                page.fill("#new-username", "")
                page.fill("#new-password", "")
                page.click("#load-records")
                page.wait_for_function(
                    "document.querySelector('#records-feedback').textContent.includes('Snapshot refreshed')"
                )
                review_interface(page, "admin")
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
                    "document.querySelector('#records-feedback').textContent.includes('Disconnected')"
                )
                assert not errors, errors
                browser.close()
                print(
                    "Chromium passed through separate frontend/API processes: admin login/roles, stored reports, server pagination/search, "
                    "text-safe details, user creation/revocation, passenger booking/cancellation, "
                    "operator session controls, configuration gates/save, logout, network error, "
                    "all four interfaces at desktop/phone widths, exact palette, confirmed arrival, mobile Stop, "
                    "stale/invalid/disconnected telemetry, fault retention on reconnect, keyboard focus, "
                    "Swagger login and CSRF-protected Try it out; no JavaScript errors."
                )
                if args.axe:
                    print(
                        "axe-core: zero detected WCAG 2.1 A/AA violations in the tested desktop and phone views."
                    )
        finally:
            if frontend is not None:
                frontend.terminate()
                frontend.wait(timeout=10)
            server.terminate()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
