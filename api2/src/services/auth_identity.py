import httpx

from src.core.exceptions import UnauthorizedRequestError


class Api1IdentityService:
    def __init__(self, me_endpoint_url: str, timeout_seconds: float) -> None:
        self._me_endpoint_url = me_endpoint_url
        self._timeout_seconds = timeout_seconds

    def get_user_id_from_token(self, token: str) -> str:
        normalized_token = token.strip()
        if not normalized_token:
            raise UnauthorizedRequestError("Unauthorized.")

        headers = {"Authorization": f"Bearer {normalized_token}"}
        try:
            with httpx.Client(timeout=self._timeout_seconds) as http_client:
                response = http_client.get(self._me_endpoint_url, headers=headers)
        except httpx.TimeoutException as exc:
            raise UnauthorizedRequestError("Authentication service timeout.") from exc
        except httpx.HTTPError as exc:
            raise UnauthorizedRequestError("Authentication service request failed.") from exc

        if response.status_code == 401:
            raise UnauthorizedRequestError("Unauthorized.")
        if response.status_code >= 500:
            raise UnauthorizedRequestError("Authentication service unavailable.")
        if response.status_code != 200:
            raise UnauthorizedRequestError("Unauthorized.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise UnauthorizedRequestError("Invalid authentication response.") from exc

        if not isinstance(payload, dict):
            raise UnauthorizedRequestError("Invalid authentication response.")

        user_id = payload.get("id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise UnauthorizedRequestError("Invalid authentication response.")

        return user_id.strip()
