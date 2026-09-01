from fastapi.testclient import TestClient

from saas_notifier.notification_api import app, realtime_client


class RecordingRealtime:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []

    def publish(self, **notification: object) -> dict[str, object]:
        self.published.append(notification)
        return {"published": True}

    def issue_token(
        self, client_id: str, channels: list[str], ttl_seconds: int = 900
    ) -> dict[str, object]:
        return {"token": "browser-session-token", "client_id": client_id}


def test_onboarding_completion_notifies_the_tenant_admin_channel() -> None:
    realtime = RecordingRealtime()
    app.dependency_overrides[realtime_client] = lambda: realtime

    with TestClient(app) as client:
        response = client.post(
            "/lifecycle-events",
            json={
                "tenant_id": "studio-42",
                "account_id": "acct-7",
                "kind": "tenant.onboarding_completed",
                "actor_name": "Mina",
            },
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "outcome": "published",
        "channel": "tenant:studio-42:admins",
    }
    assert realtime.published[0]["event"] == "admin.notification.created"
    assert realtime.published[0]["idempotency_key"] == (
        "studio-42:acct-7:tenant.onboarding_completed"
    )


def test_profile_edits_stay_out_of_the_admin_notification_feed() -> None:
    realtime = RecordingRealtime()
    app.dependency_overrides[realtime_client] = lambda: realtime

    with TestClient(app) as client:
        response = client.post(
            "/lifecycle-events",
            json={
                "tenant_id": "studio-42",
                "account_id": "acct-7",
                "kind": "account.profile_updated",
                "actor_name": "Mina",
            },
        )

    app.dependency_overrides.clear()
    assert response.json() == {"outcome": "ignored", "channel": None}
    assert realtime.published == []

