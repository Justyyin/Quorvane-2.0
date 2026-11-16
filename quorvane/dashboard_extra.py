"""Dashboard pages for the music player and the look of the dashboard, and the optional brand icons of the footer."""

import asyncio
import csv
import hashlib
import hmac
import io
import json
import logging
import re
import secrets
import time
from pathlib import Path
from typing import Any

import discord
from aiohttp import web

from . import dashlook, musicbot
from .dashboard_manage import MAX_IMAGE_BODY, parse_image
from .panels import PanelError
from .plugins import CATEGORIES, PLUGINS

log = logging.getLogger(__name__)

BRAND = Path(__file__).resolve().parent / "web" / "brand"
ACTIONS = ("join", "add", "playlist", "folder", "pause", "resume", "skip", "stop", "leave", "shuffle", "clear", "loop", "volume", "remove")


JUMP = re.compile(r"https://(?:ptb\.|canary\.)?discord\.com/channels/\d{5,20}/\d{5,20}(?:/\d{5,20})?")


class Extra:
    """The routes of these pages. Access checks, sessions and audit come from the dashboard."""

    def __init__(self, dash: Any):
        """Keep the dashboard."""
        self.dash, self.bot = dash, dash.bot

    def routes(self, app: web.Application) -> None:
        """Register the routes."""
        g = "/api/guild/{gid:\\d+}"
        app.router.add_get(g + "/music", self.music)
        app.router.add_post(g + "/music/control", self.music_control)
        app.router.add_post(g + "/music/playlist", self.music_playlist)
        app.router.add_get(g + "/logs", self.logs)
        app.router.add_post(g + "/assistant", self.assistant_ask)
        app.router.add_get(g + "/logs/export", self.logs_export)
        app.router.add_get(g + "/logs/stream", self.logs_stream)
        app.router.add_post(g + "/cases/{case:\\d+}", self.case_edit)
        app.router.add_get(g + "/members", self.members)
        app.router.add_get(g + "/transcripts", self.transcripts)
        app.router.add_get(g + "/transcripts/{name:[0-9]{10}-[a-z0-9_-]{1,80}\\.html}", self.transcript_file)
        app.router.add_post(g + "/apitoken", self.api_token)
        app.router.add_get("/api/v1/guild/{gid:\\d+}/{what:(stats|logs)}", self.public_api)
        app.router.add_post(g + "/look", self.look_save)
        app.router.add_post(g + "/look/wallpaper", self.look_wallpaper)
        app.router.add_get(g + "/look/wallpaper/{name:[0-9a-f]{16}\\.(png|jpg|gif|webp)}", self.look_wallpaper_file)
        app.router.add_get("/static/brand/{name:(discord|github)}.svg", self.brand)

    # ---- log book

    def log_rows(self, guild: Any, request: web.Request, limit: int = 0) -> list:
        """Read log entries with the filters of a request and add the picture of the member and a link to the message."""
        q = request.query

        def number(name: str) -> int:
            value = q.get(name, "0")
            return int(value) if value.isdigit() and len(value) < 16 else 0

        category = q.get("category", "")
        if category and not category.isalpha():
            raise web.HTTPBadRequest(text="unknown category")
        rows = self.bot.logbook.read(guild.id, category[:30], q.get("q", "")[:80], number("before"), number("after"), limit or number("limit") or 50, number("since"), number("until"))
        for r in rows:
            self.dress(guild, r)
        return rows

    def dress(self, guild: Any, row: dict) -> dict:
        """Add the avatar of the member and the first link to a Discord message to a log entry."""
        member = guild.get_member(int(row["uid"])) if row.get("uid") else None
        avatar = getattr(getattr(member, "display_avatar", None), "url", None)
        row["avatar"] = avatar if isinstance(avatar, str) and avatar.startswith("https://cdn.discordapp.com/") else None
        found = JUMP.search(row["text"] + " " + " ".join(str(f[1]) for f in row["fields"]))
        row["url"] = found.group(0) if found else None
        return row

    async def logs(self, request: web.Request) -> web.Response:
        """Entries of the log book, newest first, for moderators and above. after returns only what is new."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="mod")
        opts = self.bot.cfg(guild.id)["log_options"]
        return web.json_response({"entries": self.log_rows(guild, request), "stored": bool(opts["dashboard"]), "keep_days": opts["keep_days"]})

    async def logs_export(self, request: web.Request) -> web.Response:
        """The filtered log as a CSV file, at most 5000 entries."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="mod")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["time_utc", "category", "member", "member_id", "title", "text", "details"])
        for r in self.log_rows(guild, request, 5000):
            cells = [time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(r["ts"])), r["category"], r["user"], r["uid"] or "", r["title"], r["text"], "; ".join(f"{a}: {b}" for a, b in r["fields"])]
            writer.writerow([("'" + c) if isinstance(c, str) and c[:1] in "=+-@" else c for c in cells])  # no formulas in spreadsheets
        return web.Response(text=out.getvalue(), content_type="text/csv", charset="utf-8", headers={"Content-Disposition": f'attachment; filename="quorvane-logs-{guild.id}.csv"'})

    async def logs_stream(self, request: web.Request) -> web.StreamResponse:
        """New log entries as server-sent events, so the page shows them at once. Ends after 15 minutes; the browser connects again by itself."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="mod")
        listeners = self.bot.logbook.listeners.setdefault(guild.id, set())
        if len(listeners) >= 8:
            raise web.HTTPTooManyRequests(text="too many live views")
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-store", "X-Accel-Buffering": "no"})
        self.dash.harden(resp)
        await resp.prepare(request)
        listeners.add(queue)
        end = time.monotonic() + 900
        try:
            await resp.write(b": ready\n\n")
            while time.monotonic() < end:
                try:
                    row = await asyncio.wait_for(queue.get(), timeout=20)
                    await resp.write(b"data: " + json.dumps(self.dress(guild, dict(row)), ensure_ascii=False).encode("utf-8") + b"\n\n")
                except asyncio.TimeoutError:
                    await resp.write(b": ping\n\n")
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            listeners.discard(queue)
        return resp

    # ---- cases, members, transcripts

    async def case_edit(self, request: web.Request) -> web.Response:
        """Change the reason of a moderation case or delete the case. For administrators. Deleting a case does not undo the punishment."""
        s = self.dash.require(request, change=True)
        guild = self.dash.guild_for(request, s, change=True)
        data = await self.dash.read_json(request)
        case_id = int(request.match_info["case"])
        case = next((c for c in self.bot.store.cases(guild.id) if c["id"] == case_id), None)
        if case is None:
            raise web.HTTPNotFound(text="no such case")
        if data.get("delete") is True:
            self.bot.store.delete_case(guild.id, case_id)
            self.dash.audit(guild, s, f"deleted case #{case_id}")
            return web.json_response({"deleted": True})
        reason = str(data.get("reason", "")).strip()
        if not 1 <= len(reason) <= 500:
            raise web.HTTPBadRequest(text="the reason must have 1 to 500 characters")
        case["reason"] = reason
        self.dash.audit(guild, s, f"changed the reason of case #{case_id}")
        return web.json_response({"id": case_id, "reason": reason})

    async def members(self, request: web.Request) -> web.Response:
        """Search members by name or id and show what the bot knows about them. For moderators and above."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="mod")
        q = request.query.get("q", "").strip().casefold()[:60]
        pool = guild.members.values() if isinstance(guild.members, dict) else guild.members
        users, cases = self.bot.store.users(guild.id), self.bot.store.cases(guild.id)
        out = []
        for m in pool:
            uid = getattr(m, "id", None)
            if uid is None:
                continue
            names = f"{getattr(m, 'name', '')} {getattr(m, 'display_name', '')} {uid}".casefold()
            if q and q not in names:
                continue
            rec = users.get(str(uid), {})
            mine = [c for c in cases if c.get("user") == uid or str(c.get("user")) == str(uid)]
            avatar = getattr(getattr(m, "display_avatar", None), "url", None)
            joined = getattr(m, "joined_at", None)
            out.append({
                "id": str(uid), "name": str(getattr(m, "display_name", "") or getattr(m, "name", uid)), "handle": str(getattr(m, "name", "")), "bot": bool(getattr(m, "bot", False)),
                "avatar": avatar if isinstance(avatar, str) and avatar.startswith("https://cdn.discordapp.com/") else None, "joined": int(joined.timestamp()) if joined else None,
                "xp": rec.get("xp", 0), "voice_min": rec.get("voice_min", 0), "jailed": bool(rec.get("jailed")), "case_count": len(mine),
                "cases": [{"id": c["id"], "type": c["type"], "reason": str(c["reason"])[:200], "ts": c["ts"], "mod": c.get("mod_name", "")} for c in mine[-5:][::-1]],
            })
            if len(out) >= 30:
                break
        return web.json_response({"members": out, "total": len(pool)})

    def transcript_dir(self, gid: int) -> Path:
        """Where the transcripts of a server are kept."""
        return Path(self.bot.store.dir) / "transcripts" / str(int(gid))

    async def transcripts(self, request: web.Request) -> web.Response:
        """The stored ticket and mod-mail transcripts, newest first. For moderators and above."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="mod")
        folder = self.transcript_dir(guild.id)
        files = sorted(folder.glob("*.html"), reverse=True)[:200] if folder.is_dir() else []
        return web.json_response({"files": [{"name": f.name, "ts": int(f.name[:10]), "title": f.name[11:-5], "size": f.stat().st_size} for f in files]})

    async def transcript_file(self, request: web.Request) -> web.Response:
        """Download one transcript. It is sent as a file, never shown inside the dashboard."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="mod")
        path = self.transcript_dir(guild.id) / request.match_info["name"]
        if not path.is_file():
            raise web.HTTPNotFound(text="no such transcript")
        return web.Response(body=path.read_bytes(), content_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{path.name[11:]}"', "X-Content-Type-Options": "nosniff"})

    # ---- read-only API for other programs

    async def api_token(self, request: web.Request) -> web.Response:
        """Create a new API token (the old one stops working) or remove it. The token is shown once; only its hash is stored."""
        s = self.dash.require(request, change=True)
        guild = self.dash.guild_for(request, s, change=True)
        data = await self.dash.read_json(request)
        cfg = self.bot.cfg(guild.id)["dashboard_api"]
        if data.get("remove") is True:
            cfg["token_hash"] = ""
            self.dash.audit(guild, s, "removed the API token")
            return web.json_response({"active": False})
        token = "qv_" + secrets.token_urlsafe(32)
        cfg["token_hash"] = hashlib.sha256(token.encode("ascii")).hexdigest()
        self.dash.audit(guild, s, "created a new API token")
        return web.json_response({"active": True, "token": token})

    async def public_api(self, request: web.Request) -> web.Response:
        """Read-only numbers and log entries for other programs. Needs the header Authorization: Bearer with the API token of the server."""
        if not self.dash.ready():
            raise web.HTTPServiceUnavailable(text="the bot is not connected")
        guild = self.bot.get_guild(int(request.match_info["gid"]))
        sent = request.headers.get("Authorization", "")
        given = hashlib.sha256(sent[7:].encode("utf-8", "replace")).hexdigest() if sent.startswith("Bearer ") else ""
        wanted = self.bot.cfg(guild.id)["dashboard_api"]["token_hash"] if guild is not None else ""
        if not wanted or not hmac.compare_digest(given, wanted):
            raise web.HTTPUnauthorized(text="a valid API token is needed")
        if request.match_info["what"] == "logs":
            return web.json_response({"entries": self.log_rows(guild, request)})
        from .dashboard import build_stats
        data = build_stats(self.bot.cfg(guild.id), self.bot.store.cases(guild.id), 30)
        data["logs"] = self.bot.logbook.per_day(guild.id, data["days"])
        data["members"] = getattr(guild, "member_count", None)
        return web.json_response(data)

    async def assistant_ask(self, request: web.Request) -> web.Response:
        """Ask the assistant from the dashboard. For moderators and above; actions are never proposed here."""
        s = self.dash.require(request, change=True)
        guild = self.dash.guild_for(request, s, change=True, need="mod")
        data = await self.dash.read_json(request)
        question = str(data.get("question", "")).strip()
        if not 3 <= len(question) <= 600:
            raise web.HTTPBadRequest(text="the question must have 3 to 600 characters")
        cog = self.bot.get_cog("AICog")
        if cog is None or not self.bot.ai.configured(guild.id) or not self.bot.module_on(guild.id, "ai"):
            raise web.HTTPConflict(text="the AI is not set up on this server")
        from . import ai as ailib, assistant
        try:
            text, trace = await assistant.run(self.bot, guild, question, self.bot.cfg(guild.id).get("language") or "en", uid=int(s["uid"]))
        except ailib.AIError as exc:
            raise web.HTTPConflict(text=str(exc))
        fields = [["Tool", f"{t['tool']} {t['args'] or ''}".strip()[:200]] for t in trace] + [["Answer", text[:400]]]
        self.bot.logbook.add(guild.id, "assistant", "Assistant asked", question, str(s.get("name", "dashboard")), int(s["uid"]), fields)
        return web.json_response({"answer": text, "tools": [t["tool"] for t in trace]})

    # ---- music

    def music_cog(self) -> Any:
        """The music cog, on Quorvane Music or on Quorvane."""
        return self.bot.music_cog()

    async def music(self, request: web.Request) -> web.Response:
        """Player, queue, playlists and which bot plays the music."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="viewer")
        mb = getattr(self.bot, "music_bot", None)
        info: dict[str, Any] = {"second_bot": mb is not None, "enabled_in_settings": bool(musicbot.settings_of(self.bot.settings)["enabled"])}
        if mb is not None:
            ready = mb.is_ready()
            info.update({
                "bot_name": str(mb.user.name) if mb.user else "Quorvane Music", "bot_avatar": mb.user.display_avatar.url if mb.user else None,
                "online": ready, "on_server": bool(ready and mb.get_guild(guild.id)), "invite": mb.invite_url(),
            })
        else:
            info.update({"bot_name": str(self.bot.user.name) if self.bot.user else "Quorvane", "bot_avatar": self.bot.user.display_avatar.url if self.bot.user else None, "online": True, "on_server": True, "invite": None})
        cog = self.music_cog()
        target = (mb.get_guild(guild.id) if mb is not None else guild) if cog else None
        info["module_on"] = self.bot.module_on(guild.id, "music")
        info["player"] = cog.snapshot(target) if cog and target else None
        if info["player"] is None:
            conf = self.bot.cfg(guild.id)["music"]
            info["playlists"] = [{"name": k, "count": len(v.get("tracks", [])), "updated": v.get("updated", 0)} for k, v in sorted(conf.get("playlists", {}).items(), key=lambda kv: kv[0].casefold())]
        name = request.query.get("playlist")
        if name:
            for key, data in self.bot.cfg(guild.id)["music"].get("playlists", {}).items():
                if key.casefold() == name.casefold():
                    info["playlist"] = {"name": key, "tracks": data.get("tracks", [])[:500]}
                    break
        return web.json_response(info)

    async def music_control(self, request: web.Request) -> web.Response:
        """Control the player. Moderators and administrators may do this."""
        s = self.dash.require(request, change=True)
        guild = self.dash.guild_for(request, s, change=True, need="mod")
        data = await self.dash.read_json(request)
        action, value = data.get("action"), data.get("value")
        if action not in ACTIONS:
            raise web.HTTPBadRequest(text="unknown action")
        if not self.bot.module_on(guild.id, "music"):
            return web.json_response({"error": "the music module is off"}, status=409)
        cog = self.music_cog()
        mb = getattr(self.bot, "music_bot", None)
        target = mb.get_guild(guild.id) if mb is not None else guild
        if cog is None or target is None:
            return web.json_response({"error": "the music bot is not on this server"}, status=409)
        try:
            ok, text = await cog.remote(target, s["uid"], action, value)
        except (discord.DiscordException, ValueError, OSError) as exc:
            log.warning("dashboard music control failed: %s", exc)
            return web.json_response({"error": str(exc)[:300]}, status=500)
        if action in ("join", "leave", "stop", "clear"):
            self.dash.audit(guild, s, f"music: {action}")
        return web.json_response({"ok": ok, "message": text}, status=200 if ok else 409)

    async def music_playlist(self, request: web.Request) -> web.Response:
        """Create, replace, rename or delete a saved playlist. Moderators and administrators may do this."""
        s = self.dash.require(request, change=True)
        guild = self.dash.guild_for(request, s, change=True, need="mod")
        data = await self.dash.read_json(request)
        conf = self.bot.cfg(guild.id)["music"]
        lists = conf.setdefault("playlists", {})
        name = re.sub(r"\s+", " ", str(data.get("name") or "")).strip()[:40]
        if not name:
            return web.json_response({"error": "give the playlist a name"}, status=422)
        found = next((k for k in lists if k.casefold() == name.casefold()), None)
        if data.get("delete"):
            if found is None:
                raise web.HTTPNotFound(text="no such playlist")
            del lists[found]
            if conf.get("autoplay", "").casefold() == found.casefold():
                conf["autoplay"] = ""
            self.dash.audit(guild, s, f"music: playlist `{found}` deleted")
            return web.json_response({"ok": True})
        cog = self.music_cog()
        if cog is None:
            return web.json_response({"error": "music is not loaded"}, status=409)
        tracks = data.get("tracks", [])
        if not isinstance(tracks, list) or len(tracks) > 500:
            return web.json_response({"error": "at most 500 tracks"}, status=422)
        rename = re.sub(r"\s+", " ", str(data.get("rename") or "")).strip()[:40]
        if rename and found and rename.casefold() != found.casefold():
            if any(k.casefold() == rename.casefold() for k in lists):
                return web.json_response({"error": "a playlist with this name exists"}, status=422)
            lists[rename] = lists.pop(found)
            if conf.get("autoplay", "").casefold() == found.casefold():
                conf["autoplay"] = rename
            name = rename
        add = str(data.get("add") or "").strip()[:500]
        if add:
            found_tracks, error = await cog.find_tracks(guild.id, s["uid"], add)
            if error:
                return web.json_response({"error": error}, status=422)
            tracks = tracks + [{"title": t.title, "artist": t.artist, "kind": t.kind, "ref": t.ref, "length": t.length} for t in found_tracks]
        key, problem = cog.save_playlist(guild, s["uid"], name, tracks[:500])
        if problem:
            return web.json_response({"error": problem}, status=422)
        self.dash.audit(guild, s, f"music: playlist `{key}` saved")
        return web.json_response({"ok": True, "name": key})

    # ---- look

    async def look_save(self, request: web.Request) -> web.Response:
        """Store colours, menus and tabs. Administrators only."""
        s = self.dash.require(request, change=True)
        guild = self.dash.guild_for(request, s, change=True)
        data = await self.dash.read_json(request)
        cfg = self.bot.cfg(guild.id)
        try:
            cfg["look"] = dashlook.clean(data.get("look"), set(PLUGINS), {c[0] for c in CATEGORIES}, cfg.get("look"))
        except dashlook.LookError as exc:
            return web.json_response({"error": str(exc)}, status=422)
        self.dash.audit(guild, s, "dashboard look changed")
        return web.json_response({"ok": True, "look": cfg["look"]})

    async def look_wallpaper(self, request: web.Request) -> web.Response:
        """Upload or remove the wallpaper. Administrators only."""
        s = self.dash.require(request, change=True)
        guild = self.dash.guild_for(request, s, change=True)
        data = await self.dash.read_json(request, limit=MAX_IMAGE_BODY)
        look = self.bot.cfg(guild.id)["look"]
        if data.get("remove"):
            dashlook.remove_wallpaper(look, self.bot.store.dir, guild.id)
            self.dash.audit(guild, s, "dashboard wallpaper removed")
            return web.json_response({"ok": True, "wallpaper": None})
        try:
            name = dashlook.store_wallpaper(look, self.bot.store.dir, guild.id, parse_image(data.get("image")))
        except (ValueError, PanelError) as exc:
            return web.json_response({"error": str(exc)}, status=422)
        self.dash.audit(guild, s, "dashboard wallpaper changed")
        return web.json_response({"ok": True, "wallpaper": name})

    async def look_wallpaper_file(self, request: web.Request) -> web.Response:
        """The wallpaper, only for signed-in users of the server."""
        s = self.dash.require(request)
        guild = self.dash.guild_for(request, s, need="viewer")
        look = self.bot.cfg(guild.id)["look"]
        path = dashlook.wallpaper_path(look, self.bot.store.dir, guild.id)
        if path is None or path.name != request.match_info["name"]:
            raise web.HTTPNotFound(text="no wallpaper")
        kind = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}[path.suffix[1:]]
        return web.Response(body=path.read_bytes(), content_type=kind)

    async def brand(self, request: web.Request) -> web.Response:
        """An icon file for the footer links that the owner placed in quorvane/web/brand/. Missing files give 404 and the page shows its own icon."""
        path = BRAND / f"{request.match_info['name']}.svg"
        if not path.is_file() or path.stat().st_size > 64 * 1024:
            raise web.HTTPNotFound(text="no icon")
        return web.Response(body=path.read_bytes(), content_type="image/svg+xml")
