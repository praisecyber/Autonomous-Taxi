from fastapi.testclient import TestClient
from taxi.api import create_app


def test_swagger_is_self_hosted_and_schema_is_available():
    with TestClient(create_app(":memory:", "swagger-test-token", run_loop=False)) as client:
        page = client.get("/docs")
        assert page.status_code == 200
        assert "/docs/assets/swagger-init.js" in page.text
        assert "cdn.jsdelivr" not in page.text and "unpkg.com" not in page.text
        for asset in ("swagger-ui-bundle.js", "swagger-ui.css", "swagger-init.js"):
            assert client.get("/docs/assets/" + asset).status_code == 200
        schema = client.get("/openapi.json").json()
        assert schema["info"]["title"] == "Campus Taxi Prototype"
        assert "No physical vehicle motion" in schema["info"]["description"]
        schemes = schema["components"]["securitySchemes"]
        assert schemes["AccountSession"]["in"] == "cookie"
        assert schemes["LocalOperatorToken"]["scheme"] == "bearer"
        admin = schema["paths"]["/api/admin/users"]["post"]
        assert admin["tags"] == ["Administration"]
        assert admin["security"] == [{"AccountSession": []}]
        operator = schema["paths"]["/api/operator/stop"]["post"]
        assert {"LocalOperatorToken": []} in operator["security"]
        assert any(p["name"] == "X-Taxi-CSRF" for p in operator["parameters"])
        assert not schema["paths"]["/api/auth/login"]["post"].get("security")
        assert (
            schema["components"]["schemas"]["Login"]["properties"]["password"]["format"]
            == "password"
        )
        assert client.get("/admin").status_code == 404  # Product UI stays in the frontend.
        assert client.get("/docs/assets/../auth.py").status_code == 404
