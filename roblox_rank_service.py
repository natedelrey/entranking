from __future__ import annotations

import os
from typing import Any

import aiohttp
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()


def getenv(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v.strip()


SERVICE_SECRET = getenv("ROBLOX_SERVICE_SECRET")
ROBLOX_COOKIE = getenv("ROBLOX_COOKIE")
GROUP_ID = int(getenv("ROBLOX_GROUP_ID", "34438615") or "34438615")
PORT = int(getenv("PORT", "8080") or "8080")


async def _request_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async with session.request(method, url, headers=headers, json=json, timeout=30) as resp:
        text = await resp.text()
        if resp.status // 100 != 2:
            raise web.HTTPBadGateway(text=f"Roblox API {method} {url} failed {resp.status}: {text}")
        if not text:
            return {}
        return await resp.json()


def _require_secret(request: web.Request) -> None:
    if not SERVICE_SECRET:
        raise web.HTTPInternalServerError(text="ROBLOX_SERVICE_SECRET is not configured on this service.")
    if request.headers.get("X-Secret-Key") != SERVICE_SECRET:
        raise web.HTTPUnauthorized(text="Invalid X-Secret-Key")


def _headers() -> dict[str, str]:
    if not ROBLOX_COOKIE:
        raise web.HTTPInternalServerError(text="ROBLOX_COOKIE is not configured.")
    return {
        "Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}",
        "Content-Type": "application/json",
    }


async def _request_with_csrf(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Roblox returns X-CSRF-TOKEN on 403 for state-changing endpoints.
    if method.upper() in {"POST", "PATCH", "PUT", "DELETE"}:
        resp_headers: dict[str, str] = {}
        try:
            await _request_json(session, method, url, headers=headers, json=json)
        except web.HTTPBadGateway as exc:
            # Extract token from the failed response by replaying a raw request.
            async with session.request(method, url, headers=headers, json=json, timeout=30) as resp:
                resp_headers = dict(resp.headers)
                text = await resp.text()
                if resp.status != 403 or "x-csrf-token" not in {k.lower(): v for k, v in resp_headers.items()}:
                    raise web.HTTPBadGateway(text=f"Roblox API {method} {url} failed {resp.status}: {text}") from exc

            csrf = None
            for key, value in resp_headers.items():
                if key.lower() == "x-csrf-token":
                    csrf = value
                    break
            if not csrf:
                raise web.HTTPBadGateway(text="Roblox did not provide X-CSRF-TOKEN for state-changing request.") from exc

            headers = {**headers, "X-CSRF-TOKEN": csrf}
            return await _request_json(session, method, url, headers=headers, json=json)
        else:
            return {}

    return await _request_json(session, method, url, headers=headers, json=json)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"ok": True, "groupId": GROUP_ID})


async def ranks(request: web.Request) -> web.Response:
    _require_secret(request)
    headers = _headers()
    url = f"https://groups.roblox.com/v1/groups/{GROUP_ID}/roles"
    async with aiohttp.ClientSession() as session:
        data = await _request_json(session, "GET", url, headers=headers)

    roles = []
    for role in data.get("roles", []) or []:
        role_name = role.get("displayName") or role.get("name")
        role_id = role.get("id")
        roles.append({
            "id": int(role_id) if role_id is not None and str(role_id).isdigit() else role_id,
            "roleId": int(role_id) if role_id is not None and str(role_id).isdigit() else role_id,
            "name": role_name,
            "rank": role.get("rank"),
        })

    return web.json_response({"roles": roles})


async def set_rank(request: web.Request) -> web.Response:
    _require_secret(request)
    body = await request.json()
    user_id = int(body.get("robloxId") or 0)
    group_id = int(body.get("groupId") or GROUP_ID)
    role_id = body.get("roleId")
    if not user_id or not role_id:
        raise web.HTTPBadRequest(text="robloxId and roleId are required.")

    headers = _headers()
    update_url = f"https://groups.roblox.com/v1/groups/{group_id}/users/{user_id}"
    async with aiohttp.ClientSession() as session:
        await _request_with_csrf(
            session,
            "PATCH",
            update_url,
            headers=headers,
            json={"roleId": int(role_id)},
        )

    return web.json_response({"ok": True, "robloxId": user_id, "groupId": group_id, "roleId": int(role_id)})


app = web.Application()
app.add_routes([
    web.get("/health", health),
    web.get("/ranks", ranks),
    web.post("/set-rank", set_rank),
])

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
