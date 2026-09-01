from dataclasses import dataclass
from typing import Literal

LifecycleKind = Literal[
    "tenant.onboarding_completed",
    "account.suspended",
    "account.profile_updated",
]


@dataclass(frozen=True)
class LifecycleEvent:
    tenant_id: str
    account_id: str
    kind: LifecycleKind
    actor_name: str


@dataclass(frozen=True)
class AdminNotification:
    channel: str
    event: str
    data: dict[str, str]
    account_id: str
    idempotency_key: str


def notification_for(event: LifecycleEvent) -> AdminNotification | None:
    messages = {
        "tenant.onboarding_completed": (
            "Workspace ready",
            f"{event.actor_name} completed tenant onboarding.",
        ),
        "account.suspended": (
            "Account suspended",
            f"{event.actor_name} suspended an account.",
        ),
    }
    message = messages.get(event.kind)
    if message is None:
        return None

    title, body = message
    return AdminNotification(
        channel=f"tenant:{event.tenant_id}:admins",
        event="admin.notification.created",
        data={"title": title, "body": body, "source_event": event.kind},
        account_id=event.account_id,
        idempotency_key=f"{event.tenant_id}:{event.account_id}:{event.kind}",
    )

