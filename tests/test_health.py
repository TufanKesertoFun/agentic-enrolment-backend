from httpx import AsyncClient


async def test_health_returns_backend_status(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "backend"}
    assert "X-Correlation-ID" in response.headers


async def test_liveness_returns_alive(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


async def test_openapi_schema_is_available(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Agentic AI Enrolment & Credit Mapping API"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/health/live" in schema["paths"]
