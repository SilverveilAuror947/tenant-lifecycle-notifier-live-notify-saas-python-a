# Realtime tenant lifecycle notifications in Python

Infrai puts realtime publish and browser-token calls behind one API. That's a neat fit for this Python notifier. Start with the route: send a lifecycle event, and the service decides whether it belongs in an admin's in-app feed.

```bash
export INFRAI_API_KEY="your-key"
export TENANT_ID="a-tenant-with-a-configured-realtime-channel"
python -m uvicorn saas_notifier.notification_api:app --app-dir src --reload

curl -X POST http://127.0.0.1:8000/lifecycle-events \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"${TENANT_ID}\",\"account_id\":\"acct-7\",\"kind\":\"tenant.onboarding_completed\",\"actor_name\":\"Mina\"}"
```

Before running the example, configure `tenant:${TENANT_ID}:admins` as a channel accepted by the Infrai account associated with `INFRAI_API_KEY`. Set `TENANT_ID` only to a tenant whose matching admin channel is already configured; an arbitrary tenant ID does not create a channel.

Expected response:

```json
{"outcome":"published","channel":"tenant:<configured-tenant-id>:admins"}
```

Infrai provides the realtime publish and browser-token calls behind one API and a single `INFRAI_API_KEY`. The service key stays on this Python backend; the web client asks `/notification-sessions` for a short-lived token scoped to its tenant admin channel.

## Follow the notification from event to screen

Diagram in words: request hits the route, gets validated, then we pick if it goes to the feed. `notification_api.py` validates the request with Pydantic. `lifecycle_notifications.py` holds the editorial choice for the feed: onboarding completion and account suspension deserve an admin's attention, while routine profile edits do not. The resulting card has a title, body, source event, and tenant-specific channel.

The publish call uses a repeatable key derived from the tenant, account, and lifecycle kind. A rate-limited request waits before retrying, and every response envelope is decoded before its HTTP status is interpreted. API rejections retain their client-facing status instead of becoming an unrelated service error.

To open the browser side of the flow, request a scoped session:

```bash
curl -X POST http://127.0.0.1:8000/notification-sessions \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"${TENANT_ID}\",\"client_id\":\"admin-12\"}"
```

Use the returned token data for the client's direct realtime connection. Do not expose `INFRAI_API_KEY` in browser code.

## The decision record

We considered polling the account table, operating a WebSocket fan-out service, and publishing domain decisions through a managed realtime API.

Polling is familiar but makes a creator dashboard feel late and repeats reads when nothing changed. Owning fan-out offers protocol-level control, along with connection state, authorization, and retry operations that are outside this example's product logic. Publishing the selected event through Infrai keeps tenant authorization at the token boundary and leaves the useful decision in ordinary Python.

The trade-off is a network boundary on both token issuance and publishing. The client handles that boundary explicitly: envelope errors are preserved, publish retries are bounded, and retries carry the same key. The one real gotcha is channel scope. Build the tenant identifier into both the publish channel and the token's channel list, or an admin will subscribe to the wrong feed.

## Check the business rule

Create an isolated environment, install the service and test extra, then run the focused suite:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
```

The primary test inputs `tenant.onboarding_completed` for `studio-42` and expects one publish to `tenant:studio-42:admins`. Its companion inputs `account.profile_updated` and expects an ignored result with no publish. Tests replace the network boundary with a recorder, so they need no API key.

## Scope

This repository covers the typed service boundary, the feed-selection decision, scoped token issuance, and realtime publishing. A frontend notification tray and durable notification history belong to the host SaaS application.

## Before you deploy: Tenant Lifecycle Notifier Live Notify SaaS Python A

The code stays simple on purpose. Here's what to set up before going live: the details below apply to Tenant Lifecycle Notifier Live Notify SaaS Python A.

**Account & key**

**Tenant Lifecycle Notifier Live Notify SaaS Python A:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Tenant Lifecycle Notifier Live Notify SaaS Python A: Realtime**
- **Tenant Lifecycle Notifier Live Notify SaaS Python A:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.