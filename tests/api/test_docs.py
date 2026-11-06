"""Regression tests for the OpenAPI schema and documentation routes."""

from __future__ import annotations

from django.urls import reverse


def test_schema_documents_every_endpoint_and_bearer_auth(client):
    response = client.get(
        reverse("schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == 200
    schema = response.json()
    assert schema["openapi"].startswith("3.")

    expected_operations = {
        "/healthz": {"get"},
        "/auth/check": {"post"},
        "/auth/login": {"post"},
        "/auth/register": {"post"},
        "/auth/refresh": {"post"},
        "/auth/logout": {"post"},
        "/auth/session": {"get"},
        "/auth/otp/send": {"post"},
        "/auth/otp/verify": {"post"},
        "/api/me": {"get", "patch"},
    }
    for path, methods in expected_operations.items():
        assert path in schema["paths"]
        assert methods <= set(schema["paths"][path])

    # The schema endpoint itself is not part of the API surface.
    assert "/api/schema/" not in schema["paths"]

    scheme = schema["components"]["securitySchemes"]["bearerAuth"]
    assert scheme["type"] == "http"
    assert scheme["scheme"] == "bearer"
    assert scheme["bearerFormat"] == "JWT"

    protected = [
        ("/auth/session", "get"),
        ("/api/me", "get"),
        ("/api/me", "patch"),
    ]
    for path, method in protected:
        assert schema["paths"][path][method]["security"] == [
            {"bearerAuth": []}
        ]

    public = [
        ("/healthz", "get"),
        ("/auth/login", "post"),
        ("/auth/register", "post"),
    ]
    for path, method in public:
        assert not schema["paths"][path][method].get("security")


def test_swagger_ui_uses_schema_endpoint(client):
    response = client.get(reverse("swagger-ui"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert b"swagger-ui" in response.content.lower()
    assert b"/api/schema/" in response.content


def test_redoc_uses_schema_endpoint(client):
    response = client.get(reverse("redoc"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert b"redoc" in response.content.lower()
    assert b"/api/schema/" in response.content
