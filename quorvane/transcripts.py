"""Transcripts of tickets and mod-mail as one HTML file that opens in any browser.

The file needs nothing from the internet: the look, the pictures of the members and the images of the conversation are inside it.
Every text of a member is escaped, and the file carries its own content security policy that forbids scripts.
"""

import base64
import html
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import i18n

log = logging.getLogger(__name__)

# Texts of the file; scripts/missing_texts.py checks that every language has them
TEXTS = (
    "opened by", "opened", "closed by", "closed", "handled by", "reason", "type", "member", "server",
    "What they wrote", "History", "Staff notes", "Conversation", "Staff", "Opened", "Claimed", "Closed", "Added", "Removed", "Renamed",
    "by {name}", "No messages.", "Saved by Quorvane when the ticket closed.", "Saved by Quorvane when the conversation closed.",
    "The file was too large to keep.", "Ticket {number}", "Mod-mail",
)

MAX_AVATAR = 60_000
MAX_IMAGE = 1_000_000
MAX_IMAGES_TOTAL = 4_000_000
MAX_BANNER = 700_000
HEX = re.compile(r"#[0-9a-fA-F]{6}")
MAGIC = ((b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpeg"), (b"GIF87a", "gif"), (b"GIF89a", "gif"))

CSS = """
:root{--ink:#e9e6df;--muted:#8f8b82;--faint:#5c5952;--rule:#2b2a27;--gold:ACCENT;--note:#141414;--staff:color-mix(in srgb,var(--gold) 7%,transparent)}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",system-ui,sans-serif;
background:radial-gradient(ellipse 70% 45% at 50% 0%,color-mix(in srgb,var(--gold) 22%,transparent),transparent 70%),radial-gradient(ellipse 60% 50% at 15% 35%,rgba(255,255,255,.05),transparent 70%),#08080a}
a{color:var(--gold);overflow-wrap:anywhere;text-decoration-color:color-mix(in srgb,var(--gold) 40%,transparent)}
.m{color:var(--muted)}
.wrap{width:min(860px,100%);margin:auto;padding:48px 16px 64px}
.note{background:var(--note);border:1px solid rgba(255,255,255,.07);border-radius:16px;box-shadow:0 30px 80px rgba(0,0,0,.6),0 0 0 1px rgba(0,0,0,.4);overflow:hidden}
.bar{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--rule);color:var(--faint);font-size:12px}
.bar i{width:11px;height:11px;border-radius:50%;background:#2e2d2a;display:inline-block}
.bar .logo{width:18px;height:18px;border-radius:5px;margin-left:8px}
.bar span{margin-left:auto;font-family:ui-monospace,"SF Mono",Menlo,monospace}
.page{padding:28px 40px 40px}
.banner{display:block;width:100%;aspect-ratio:2720/960;object-fit:cover;border-bottom:1px solid var(--rule)}
h1,h2{font-weight:650;letter-spacing:-.01em}
h1{font-size:clamp(24px,4vw,32px);margin:0 0 4px}h1::before,h2::before{color:var(--faint);font-weight:400;font-family:ui-monospace,"SF Mono",Menlo,monospace;margin-right:.45em}
h1::before{content:"#"}h2::before{content:"##"}
h2{font-size:17px;margin:34px 0 10px}
.sub{color:var(--muted);margin:0}
hr{border:0;border-top:1px solid var(--rule);margin:24px 0}
.props{display:grid;grid-template-columns:120px 1fr;gap:6px 16px;margin:20px 0 0;font-size:14px}
.props dt{color:var(--muted);font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12px;padding-top:2px}.props dd{margin:0}
blockquote{margin:0;padding:2px 0 2px 16px;border-left:3px solid var(--gold);color:var(--ink);white-space:pre-wrap;overflow-wrap:anywhere}
ul.log{list-style:none;margin:0;padding:0}
ul.log li{display:grid;grid-template-columns:20px 170px 1fr;gap:8px;padding:5px 0;font-size:14px}
ul.log li::before{content:"\\2013";color:var(--faint)}
ul.log time{color:var(--muted);font-size:13px}ul.log small{display:block;color:var(--muted);white-space:pre-wrap;overflow-wrap:anywhere}
.msg{display:grid;grid-template-columns:32px 1fr;gap:12px;padding:12px 10px;margin:0 -10px;border-radius:10px}
.msg.staff{background:var(--staff)}
.av{width:32px;height:32px;border-radius:50%;object-fit:cover;background:#26252a;display:grid;place-items:center;font-size:13px;font-weight:700;color:var(--muted)}
.msg header{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:14px}.msg header time{margin-left:auto;color:var(--faint);font-size:12px}
.tag{color:var(--gold);border:1px solid color-mix(in srgb,var(--gold) 45%,transparent);border-radius:999px;padding:0 7px;font-size:11px;font-weight:600}
.t{margin-top:2px;overflow-wrap:anywhere;white-space:pre-wrap}
.file{margin-top:8px;font-size:13px}.file img{display:block;max-width:min(520px,100%);max-height:400px;border-radius:8px;margin-bottom:4px;border:1px solid var(--rule)}
.empty{color:var(--muted);font-style:italic}
footer{margin-top:20px;text-align:center;color:var(--faint);font-size:12px}
@media(max-width:640px){.page{padding:22px 18px 28px}.props{grid-template-columns:1fr}.props dt{padding-top:8px}ul.log li{grid-template-columns:14px 1fr}ul.log time{grid-column:2}ul.log span{grid-column:2}.msg header time{width:100%;margin:0}}
"""


def data_uri(data: Optional[bytes], limit: int) -> Optional[str]:
    """Turn the bytes of a picture into a data address, or None when it is no known picture or too large."""
    if not data or len(data) > limit:
        return None
    kind = next((name for magic, name in MAGIC if data.startswith(magic)), None)
    if kind is None and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = "webp"
    if kind is None:
        return None
    return f"data:image/{kind};base64,{base64.b64encode(data).decode('ascii')}"


def stamp(ts: Any) -> str:
    """A time element in UTC, from seconds or a datetime."""
    when = ts if isinstance(ts, datetime) else datetime.fromtimestamp(float(ts), tz=timezone.utc)
    when = when.astimezone(timezone.utc)
    return f'<time datetime="{when:%Y-%m-%dT%H:%M:%SZ}">{when:%Y-%m-%d %H:%M} UTC</time>'


def rich(text: str) -> str:
    """Escape a text and make its http and https addresses clickable."""
    safe = html.escape(text or "", quote=True)
    return re.sub(r"https?://[^\s<]+", lambda m: f'<a href="{m.group(0)}" rel="noopener noreferrer">{m.group(0)}</a>', safe)


def person(name: Any, handle: Any = None) -> str:
    """A name with the user name behind it."""
    out = html.escape(str(name))
    if handle:
        out += f' <span class="m">@{html.escape(str(handle))}</span>'
    return out


def render(doc: dict, lang: str = "en", staff_view: bool = True) -> bytes:
    """Build the file. Staff notes are left out unless staff_view is set, so the copy for the member never has them."""
    def t(text: str, **values: Any) -> str:
        return html.escape(i18n.tr(lang, text, **values))

    wanted = doc.get("accent")
    accent: str = wanted if isinstance(wanted, str) and HEX.fullmatch(wanted) else "#dcc08a"
    title = html.escape(str(doc.get("title", "")))
    out = [
        '<!doctype html>', f'<html lang="{html.escape(lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:">',
        f'<title>{title} · Quorvane</title>', f'<style>{CSS.replace("ACCENT", accent)}</style></head>',
        '<body><div class="wrap"><article class="note">', '<div class="bar"><i></i><i></i><i></i>',
    ]
    if doc.get("logo"):
        out.append(f'<img class="logo" src="{doc["logo"]}" alt="">')
    out.append(f'<span>{html.escape(str(doc.get("file", "transcript")))}.html</span></div>')
    if doc.get("banner"):
        out.append(f'<img class="banner" src="{doc["banner"]}" alt="">')
    out.append(f'<div class="page"><h1>{title}</h1><p class="sub">{html.escape(str(doc.get("subtitle", "")))}</p><dl class="props">')
    for label, value in doc.get("props", []):
        shown = person(*value) if isinstance(value, tuple) else (stamp(value) if isinstance(value, (int, float, datetime)) else html.escape(str(value)))
        out.append(f"<dt>{t(label)}</dt><dd>{shown}</dd>")
    out.append("</dl>")
    if doc.get("quote"):
        out.append(f'<h2>{t("What they wrote")}</h2><blockquote>{rich(doc["quote"])}</blockquote>')
    if doc.get("history"):
        out.append(f'<h2>{t("History")}</h2><ul class="log">')
        for ts, verb, who, detail in doc["history"]:
            small = f"<small>{html.escape(str(detail))}</small>" if detail else ""
            out.append(f'<li>{stamp(ts)}<span><b>{t(verb)}</b> {t("by {name}", name=who)}{small}</span></li>')
        out.append("</ul>")
    if staff_view and doc.get("notes"):
        out.append(f'<h2>{t("Staff notes")}</h2><ul class="log">')
        for ts, who, text in doc["notes"]:
            out.append(f"<li>{stamp(ts)}<span><b>{html.escape(str(who))}</b><small>{html.escape(str(text))}</small></span></li>")
        out.append("</ul>")
    out.append(f'<hr><h2>{t("Conversation")}</h2>')
    messages = doc.get("messages", [])
    if not messages:
        out.append(f'<p class="empty">{t("No messages.")}</p>')
    for m in messages:
        name = str(m.get("name") or "?")
        avatar = f'<img class="av" src="{m["avatar"]}" alt="">' if m.get("avatar") else f'<span class="av">{html.escape(name[:1].upper())}</span>'
        tag = f'<span class="tag">{t("Staff")}</span>' if m.get("staff") else ""
        handle = f'<span class="m">@{html.escape(str(m["handle"]))}</span>' if m.get("handle") else ""
        body = f'<div class="t">{rich(m.get("text", ""))}</div>' if m.get("text") else ""
        for f in m.get("files", []):
            label = html.escape(str(f.get("name", "file")))
            if f.get("image"):
                body += f'<div class="file"><img src="{f["image"]}" alt="{label}"><span class="m">{label}</span></div>'
            else:
                body += f'<div class="file"><span class="m">{label} · {t("The file was too large to keep.")}</span></div>'
        out.append(f'<article class="msg{" staff" if m.get("staff") else ""}">{avatar}<div><header><b>{html.escape(name)}</b>{tag}{handle}{stamp(m["ts"])}</header>{body}</div></article>')
    closing = "Saved by Quorvane when the conversation closed." if doc.get("kind") == "modmail" else "Saved by Quorvane when the ticket closed."
    out.append(f"</div></article><footer>{t(closing)}</footer></div></body></html>")
    return "\n".join(out).encode("utf-8")


def plain(guild: Any, text: str) -> str:
    """Replace the mentions of members, roles and channels with their names."""
    def member(m: "re.Match[str]") -> str:
        found = guild.get_member(int(m.group(1)))
        return f"@{found.display_name}" if found else m.group(0)

    def role(m: "re.Match[str]") -> str:
        found = guild.get_role(int(m.group(1)))
        return f"@{found.name}" if found else m.group(0)

    def channel(m: "re.Match[str]") -> str:
        found = guild.get_channel(int(m.group(1)))
        return f"#{found.name}" if found else m.group(0)

    text = re.sub(r"<@!?(\d{5,20})>", member, text or "")
    text = re.sub(r"<@&(\d{5,20})>", role, text)
    return re.sub(r"<#(\d{5,20})>", channel, text)


async def picture(asset: Any, limit: int, size: int) -> Optional[str]:
    """Read a picture from Discord as a data address. A failure only costs the picture."""
    if asset is None:
        return None
    try:
        return data_uri(await asset.replace(size=size, static_format="png").read(), limit)
    except Exception as exc:  # the network and Discord decide here, the transcript must still be written
        log.info("picture for a transcript could not be read: %s", exc)
        return None


async def conversation(channel: Any, is_staff: Any) -> list:
    """Read every message of a channel, oldest first, with the pictures of the authors and the images they sent."""
    guild, avatars, spent, out = channel.guild, {}, 0, []
    async for m in channel.history(limit=None, oldest_first=True):
        parts = [plain(guild, m.content)] if m.content else []
        for e in getattr(m, "embeds", []):
            parts.extend(plain(guild, str(x)) for x in (e.title, e.description) if x)
        files = []
        for a in getattr(m, "attachments", []):
            image = None
            if (a.content_type or "").startswith("image/") and a.size <= MAX_IMAGE and spent + a.size <= MAX_IMAGES_TOTAL:
                try:
                    image = data_uri(await a.read(), MAX_IMAGE)
                except Exception as exc:  # same as above: keep the transcript, drop the image
                    log.info("attachment for a transcript could not be read: %s", exc)
                if image:
                    spent += a.size
            files.append({"name": a.filename, "image": image})
        if not parts and not files:
            continue
        author = m.author
        if author.id not in avatars:
            avatars[author.id] = await picture(getattr(author, "display_avatar", None), MAX_AVATAR, 64)
        out.append({
            "name": getattr(author, "display_name", None) or author.name, "handle": author.name, "staff": bool(author.bot or is_staff(author)),
            "ts": m.created_at, "text": "\n".join(parts), "avatar": avatars[author.id], "files": files,
        })
    return out


def keep(bot: Any, guild: Any, name: str, data: bytes) -> None:
    """Store the team copy of a transcript for the dashboard, when the log book is kept."""
    if not bot.cfg(guild.id)["log_options"]["dashboard"]:
        return
    try:
        folder = Path(bot.store.dir) / "transcripts" / str(int(guild.id))
        folder.mkdir(parents=True, exist_ok=True)
        clean = re.sub(r"[^a-z0-9_-]", "-", str(name).lower())[:80] or "transcript"
        (folder / f"{int(time.time()):010d}-{clean}.html").write_bytes(data)
    except OSError as exc:
        log.warning("transcript could not be stored: %s", exc)


def prune(bot: Any, gid: int, keep_days: int) -> int:
    """Delete stored transcripts that are older than the days the server chose. Returns how many were deleted."""
    folder = Path(bot.store.dir) / "transcripts" / str(int(gid))
    limit, n = time.time() - max(1, keep_days) * 86400, 0
    for f in folder.glob("*.html") if folder.is_dir() else ():
        if f.name[:10].isdigit() and int(f.name[:10]) < limit:
            f.unlink(missing_ok=True)
            n += 1
    return n


async def dress(doc: dict, bot: Any, guild: Any) -> dict:
    """Add the icon and banner of the server and the accent colour of its dashboard."""
    doc["logo"] = await picture(getattr(guild, "icon", None), MAX_AVATAR, 64)
    doc["banner"] = await picture(getattr(guild, "banner", None), MAX_BANNER, 1024)
    doc["accent"] = (bot.cfg(guild.id).get("look") or {}).get("accent")
    return doc
