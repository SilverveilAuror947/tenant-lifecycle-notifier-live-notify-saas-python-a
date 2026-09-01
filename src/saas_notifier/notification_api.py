from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_realtime import InfraiError, InfraiRealtime
from .lifecycle_notifications import LifecycleEvent, LifecycleKind, notification_for


class LifecycleEventRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    kind: LifecycleKind
    actor_name: str = Field(min_length=1)


class DispatchResult(BaseModel):
    outcome: Literal["published", "ignored"]
    channel: str | None = None


class SessionRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)


class SessionResult(BaseModel):
    channel: str
    token_data: dict[str, object]


def realtime_client() -> InfraiRealtime:
    return InfraiRealtime()


RealtimeDep = Annotated[InfraiRealtime, Depends(realtime_client)]
app = FastAPI(title="Tenant lifecycle notifier")


@app.post("/lifecycle-events", response_model=DispatchResult)
def dispatch_lifecycle_event(
    request: LifecycleEventRequest, realtime: RealtimeDep
) -> DispatchResult:
    notification = notification_for(LifecycleEvent(**request.model_dump()))
    if notification is None:
        return DispatchResult(outcome="ignored")

    try:
        realtime.publish(
            channel=notification.channel,
            event=notification.event,
            data=notification.data,
            account_id=notification.account_id,
            idempotency_key=notification.idempotency_key,
        )
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return DispatchResult(outcome="published", channel=notification.channel)


@app.post("/notification-sessions", response_model=SessionResult)
def create_notification_session(
    request: SessionRequest, realtime: RealtimeDep
) -> SessionResult:
    channel = f"tenant:{request.tenant_id}:admins"
    try:
        token_data = realtime.issue_token(request.client_id, [channel])
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return SessionResult(channel=channel, token_data=token_data)

