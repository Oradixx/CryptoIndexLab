"""Token validation through api1 /me (Api1IdentityService).

api1 is emulated with httpx.MockTransport: no request leaves the process.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from src.core.exceptions import UnauthorizedRequestError
from src.services.auth_identity import Api1IdentityService

ME_URL = "http://api1.test.invalid/me"


def fake_api1(request):
    """Answers like api1 /me for a single known token."""
    if request.headers.get("Authorization") == "Bearer good-token":
        return httpx.Response(200, json={"id": "user-42", "email": "a@example.com"})
    return httpx.Response(401, json={"detail": "Unauthorized."})


@pytest.fixture
def identity():
    return Api1IdentityService(me_endpoint_url=ME_URL, timeout_seconds=1)


def test_valid_token_resolves_to_the_user_id(mock_http, identity):
    requests = mock_http(fake_api1)

    assert identity.get_user_id_from_token("  good-token  ") == "user-42"
    (request,) = requests
    assert str(request.url) == ME_URL
    assert request.headers["Authorization"] == "Bearer good-token"


def test_user_id_is_trimmed(mock_http, identity):
    mock_http(lambda request: httpx.Response(200, json={"id": "  user-42 "}))

    assert identity.get_user_id_from_token("token") == "user-42"


@pytest.mark.parametrize("token", ["", "   "])
def test_blank_token_is_rejected_without_calling_api1(mock_http, identity, token):
    requests = mock_http(fake_api1)

    with pytest.raises(UnauthorizedRequestError, match="Unauthorized."):
        identity.get_user_id_from_token(token)
    assert requests == []


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(401), "Unauthorized."),
        (httpx.Response(403), "Unauthorized."),
        (httpx.Response(404), "Unauthorized."),
        (httpx.Response(500), "Authentication service unavailable."),
        (httpx.Response(503), "Authentication service unavailable."),
        (httpx.Response(200, text="not json"), "Invalid authentication response."),
        (httpx.Response(200, json=["user-42"]), "Invalid authentication response."),
        (httpx.Response(200, json={"email": "a@example.com"}), "Invalid authentication response."),
        (httpx.Response(200, json={"id": 42}), "Invalid authentication response."),
        (httpx.Response(200, json={"id": "   "}), "Invalid authentication response."),
    ],
    ids=[
        "401",
        "403",
        "404",
        "500",
        "503",
        "not-json",
        "not-an-object",
        "no-id",
        "id-not-a-string",
        "blank-id",
    ],
)
def test_api1_answers_other_than_a_user_are_rejected(mock_http, identity, response, message):
    mock_http(lambda request: response)

    with pytest.raises(UnauthorizedRequestError) as exc_info:
        identity.get_user_id_from_token("token")

    assert str(exc_info.value) == message


def test_api1_timeout_is_rejected(mock_http, identity):
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    mock_http(handler)

    with pytest.raises(UnauthorizedRequestError, match="Authentication service timeout."):
        identity.get_user_id_from_token("token")


def test_api1_unreachable_is_rejected(mock_http, identity):
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    mock_http(handler)

    with pytest.raises(UnauthorizedRequestError, match="Authentication service request failed."):
        identity.get_user_id_from_token("token")


def test_non_ascii_token_is_rejected(mock_http, identity):
    mock_http(fake_api1)

    with pytest.raises(UnauthorizedRequestError):
        identity.get_user_id_from_token("abc.é")


# --- Wired into the application --------------------------------------------


@pytest.fixture
def client_with_real_identity(app, identity):
    app.state.identity_service = identity
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_routes_use_the_user_id_returned_by_api1(mock_http, client_with_real_identity):
    mock_http(fake_api1)

    response = client_with_real_identity.post(
        "/indexes",
        json={"name": "Mine", "assets": [{"symbol": "BTC", "weight": 100}]},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == "user-42"


@pytest.mark.parametrize(
    "handler",
    [fake_api1, lambda request: httpx.Response(503)],
    ids=["token-refused-by-api1", "api1-down"],
)
def test_routes_answer_401_when_api1_does_not_confirm_the_token(
    mock_http, client_with_real_identity, handler
):
    mock_http(handler)

    response = client_with_real_identity.get(
        "/indexes", headers={"Authorization": "Bearer bad-token"}
    )

    assert response.status_code == 401


def test_routes_answer_401_to_a_non_ascii_token(mock_http, client_with_real_identity):
    mock_http(fake_api1)

    response = client_with_real_identity.get(
        "/indexes", headers={"Authorization": b"Bearer abc.\xe9"}
    )

    assert response.status_code == 401
