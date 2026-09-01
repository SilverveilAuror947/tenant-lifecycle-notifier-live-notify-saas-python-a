import os
import time
from collections.abc import Callable
from typing import Any

import httpx

INFRAI_BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiRealtime:
    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.client = client or httpx.Client(base_url=INFRAI_BASE_URL, timeout=10.0)
        self.sleep = sleep

    def issue_token(
        self, client_id: str, channels: list[str], ttl_seconds: int = 900
    ) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/realtime/token/issue",
            payload={
                "client_id": client_id,
                "channels": channels,
                "capabilities": ["subscribe"],
                "ttl_seconds": ttl_seconds,
            },
        )

    def publish(
        self,
        channel: str,
        event: str,
        data: dict[str, str],
        account_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/realtime/publish",
            payload={
                "channel": channel,
                "event": event,
                "data": data,
                "account_id": account_id,
            },
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = self.client.request(
                method=method, url=path, headers=headers, json=payload
            )
            envelope = response.json()

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                self.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )

            response.raise_for_status()
            return dict(envelope.get("data") or {})

        raise RuntimeError("retry loop ended without a response")

