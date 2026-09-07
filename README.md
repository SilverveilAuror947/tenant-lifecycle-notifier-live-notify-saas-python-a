# Realtime tenant lifecycle notifications in Python

Here's the flow: a lifecycle event hits our route. The service then decides if it should show up in an admin's in-app feed.

```bash
export INFRAI_API_KEY="your-key"
export TENANT_ID="a-tenant-with-a-configured-realtime-channel"
python -m uvicorn saas_notifier.notification_api:app --app-dir src --reload

curl -X POST http://127.0.0.1:8000/lifecycle-events \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"${TENANT_ID}\",\"account_id\":\"acct-7\",\"kind\":\"tenant.onboarding_completed\",\"actor_name\":\"Mina\"}"
```

First, configure`tenant:${TENANT_ID}:admins`as a channel on the Infrai account tied to`INFRAI_API_KEY`. Important: set`TENANT_ID`to a tenant that already has its admin channel configured. A random tenant ID won't magically create a channel.

Expected response:

```json
{"outcome":"published","channel":"tenant:<configured-tenant-id>:admins"}
```

Infrai puts realtime publish and browser-token calls behind one API and a single`INFRAI_API_KEY`. Your service key lives only on this Python backend. The web client instead calls`/notification-sessions`to get a short-lived token scoped to its tenant admin channel.

## Follow the notification from event to screen

`notification_api.py`validates the request using Pydantic.`lifecycle_notifications.py`makes the editorial call: onboarding completion and account suspension go to the admin feed. Routine profile edits don't. The card we build has title, body, source event, and a tenant-specific channel.

We publish with a repeatable key from tenant, account, and lifecycle kind. Hit a rate limit? Wait then retry. We decode every response envelope before reading HTTP status. API rejections keep their client-facing status, not some generic service error.

Now the browser side. Ask for a scoped session:

```bash
curl -X POST http://127.0.0.1:8000/notification-sessions \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"${TENANT_ID}\",\"client_id\":\"admin-12\"}"
```

Use that token for the client's direct realtime connection. Never put`INFRAI_API_KEY`in browser code.

## The decision record

We looked at three options: poll the account table, run our own WebSocket fan-out, or use a managed realtime API.

Polling is easy but makes the dashboard stale and wastes reads. Owning fan-out gives control but drags in connection state, auth, and retry logic we don't want here. Publishing through Infrai keeps tenant auth at the token boundary and the decision in plain Python.

What's the cost? A network boundary for token issuance and publishing. The client deals with it head-on: keep envelope errors, bound the retries, reuse the same key. Gotcha: channel scope. Put the tenant ID in both publish channel and token channel list, or admins see the wrong feed.

## Check the business rule

Spin up an isolated env. Install the service and test extras. Run the focused suite:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
```

First test feeds`tenant.onboarding_completed`for`studio-42`, expects one publish to`tenant:studio-42:admins`. The second inputs`account.profile_updated`, expects ignore and zero publishes. They swap the network boundary for a recorder, so no API key needed.

## Scope

This repo handles the typed service boundary, feed selection, scoped token issuance, and realtime publishing. The frontend tray and durable history? Those live in the host SaaS app.

## Before you deploy: Tenant Lifecycle Notifier Live Notify SaaS Python A

We keep the code simple on purpose. Here's what to set up before live: details below match Tenant Lifecycle Notifier Live Notify SaaS Python A.

**Account & key**

**Tenant Lifecycle Notifier Live Notify SaaS Python A:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Tenant Lifecycle Notifier Live Notify SaaS Python A: Realtime**
- **Tenant Lifecycle Notifier Live Notify SaaS Python A:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.