# Roblox Rank Service

Small `aiohttp` service for listing Roblox group roles and setting a user's group role with a Roblox account cookie.

## Environment variables

Set these variables in your host, Railway project, or local `.env` file:

| Variable | Required | Description |
| --- | --- | --- |
| `ROBLOX_COOKIE` | Required unless you send `X-Roblox-Cookie` per request | The Roblox account `.ROBLOSECURITY` cookie used to call Roblox group ranking endpoints. You can paste either the raw cookie value or the full `.ROBLOSECURITY=...` string. |
| `ROBLOX_GROUP_ID` | Optional | Default group ID used by `/health`, `/ranks`, and `/set-rank` when the request body does not include `groupId`. Defaults to `34438615`. |
| `PORT` | Optional | HTTP port for the service. Defaults to `8080`. |

`ROBLOX_SERVICE_SECRET` and `X-Secret-Key` are not used by this service. Requests authenticate to Roblox with the Roblox account cookie instead.

## Local setup

Create a `.env` file:

```env
ROBLOX_COOKIE=.ROBLOSECURITY=your_cookie_here
ROBLOX_GROUP_ID=34438615
PORT=8080
```

Then run:

```bash
python roblox_rank_service.py
```

## Request examples

List roles for the configured group:

```bash
curl http://localhost:8080/ranks
```

Set a user's rank:

```bash
curl -X POST http://localhost:8080/set-rank \
  -H 'Content-Type: application/json' \
  -d '{"robloxId":123456789,"roleId":987654321}'
```

You can also avoid storing `ROBLOX_COOKIE` in the environment by sending the cookie on each request:

```bash
curl -X POST http://localhost:8080/set-rank \
  -H 'Content-Type: application/json' \
  -H 'X-Roblox-Cookie: .ROBLOSECURITY=your_cookie_here' \
  -d '{"robloxId":123456789,"groupId":34438615,"roleId":987654321}'
```

Keep the Roblox cookie private. Anyone with the cookie can act as that Roblox account wherever the account has permission.
