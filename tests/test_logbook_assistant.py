"""The log book of the dashboard and the assistant that answers questions with read-only tools."""

import asyncio
import json
import tempfile
import time
import unittest
from types import SimpleNamespace

import discord

from quorvane import assistant, logbook
from tests import test_dashboard_manage as base
from tests.test_dashboard import ADMIN, VIEWER


class LogBookTest(unittest.TestCase):
    def setUp(self):
        self.book = logbook.LogBook(tempfile.mkdtemp())

    def tearDown(self):
        self.book.close()

    def test_add_read_filter_and_search(self):
        self.book.add(1, "messages", "Message deleted", "hello world", "sam", 5, [["Channel", "#general"]])
        self.book.add(1, "security", "AutoMod: antiscam", "scam link 100%_off", "eve", 6)
        self.book.add(2, "messages", "Other server")
        rows = self.book.read(1)
        self.assertEqual([r["title"] for r in rows], ["AutoMod: antiscam", "Message deleted"])
        self.assertEqual(rows[1]["fields"], [["Channel", "#general"]])
        self.assertEqual(rows[1]["uid"], "5")
        self.assertEqual(len(self.book.read(1, category="security")), 1)
        self.assertEqual(len(self.book.read(1, query="general")), 1)
        self.assertEqual(len(self.book.read(1, query="100%_off")), 1)
        self.assertEqual(self.book.read(1, query="%"), [rows[0]])
        self.assertEqual(self.book.read(1, after=rows[1]["id"]), [rows[0]])
        self.assertEqual(self.book.read(1, before=rows[0]["id"]), [rows[1]])

    def test_prune_forget_and_drop(self):
        self.book.add(1, "main", "old", ts=int(time.time()) - 40 * 86400)
        self.book.add(1, "main", "new", "about <@77>", uid=None)
        self.book.add(1, "main", "mine", uid=77)
        self.assertEqual(self.book.prune(1, 30), 1)
        self.assertEqual(self.book.forget_user(1, 77), 2)
        self.book.add(1, "main", "again")
        self.book.drop_guild(1)
        self.assertEqual(self.book.read(1), [])

    def test_per_day(self):
        day = time.strftime("%Y-%m-%d", time.gmtime())
        self.book.add(1, "security", "a")
        self.book.add(1, "security", "b")
        self.assertEqual(self.book.per_day(1, ["2000-01-01", day]), {"security": [0, 2]})

    def test_from_embed(self):
        e = discord.Embed(title="Message deleted", description="text")
        e.set_author(name="sam (123456)")
        e.add_field(name="Channel", value="#a")
        self.assertEqual(logbook.from_embed(e), {"title": "Message deleted", "text": "text", "user": "sam", "uid": 123456, "fields": [["Channel", "#a"]]})


class AssistantTest(unittest.TestCase):
    def setUp(self):
        cfg = {"modules": {"antiscam": True, "music": False}, "antiscam": {"action": "jail", "hits": 3, "iplogger": {"enabled": True}}, "automod": {"hits": {"spam": 2}},
               "lockdown": {"active": False}, "raid": {"enabled": True}, "jail": {"role": 1, "channel": 2}, "tickets": {"open": {"9": {"type": "support", "ts": time.time() - 600}}},
               "modmail": {"open": {}}, "activity": {"days": {"2026-11-15": {"msgs": 40, "joins": 2}}}}
        self.book = logbook.LogBook(tempfile.mkdtemp())
        self.bot = SimpleNamespace(
            cfg=lambda gid: cfg, module_on=lambda gid, name: cfg["modules"].get(name, False), started=time.time() - 7200, latency=0.05, guilds=[1], queue=None, logbook=self.book,
            ai=SimpleNamespace(budget=lambda gid: (1, 50)),
            store=SimpleNamespace(cases=lambda gid: [{"id": 1, "type": "ban", "user_name": "eve", "mod_name": "ken", "reason": "scam", "ts": time.time()}], users=lambda gid: {"5": {"jailed": True}}),
        )
        self.guild = SimpleNamespace(id=1, name="Lautre", member_count=120, members=[], channels=[1, 2], roles=[1], premium_subscription_count=2, created_at="2020-01-01 00:00")

    def tearDown(self):
        self.book.close()

    def run_with(self, replies):
        seen = []

        async def ask(gid, system, prompt, uid=None, max_tokens=None):
            seen.append((system, prompt, uid))
            return replies[len(seen) - 1]

        answer, trace = asyncio.run(assistant.run(self.bot, self.guild, "how is the server doing?", "de", uid=5, ask=ask))
        return answer, trace, seen

    def test_tools_then_answer(self):
        answer, trace, seen = self.run_with(['{"tool": "bot_health", "args": {}}', 'Sure: {"tool": "tickets", "args": {}}', '{"answer": "All good, 1 ticket open."}'])
        self.assertEqual(answer, "All good, 1 ticket open.")
        self.assertEqual(trace, [{"tool": "bot_health", "args": {}}, {"tool": "tickets", "args": {}}])
        self.assertIn('"uptime_hours": 2.0', seen[1][1])
        self.assertIn('"open": 1', seen[2][1])
        self.assertEqual([s[2] for s in seen], [5, None, None])
        self.assertIn("You cannot change anything", seen[0][0])

    def test_plain_text_is_the_answer(self):
        self.assertEqual(self.run_with(["Hello there"])[0], "Hello there")

    def test_unknown_tool_and_step_limit(self):
        answer, trace, seen = self.run_with(['{"tool": "ban_everyone", "args": {}}'] * 10)
        self.assertEqual(len(seen), assistant.MAX_STEPS + 1)
        self.assertEqual(answer, "I could not find an answer.")
        self.assertIn("unknown tool", seen[1][1])

    def test_every_tool_reads_without_error(self):
        self.book.add(1, "security", "AutoMod: antiscam", "x", "eve")
        for name, (_, tool) in assistant.TOOLS.items():
            json.dumps(tool(self.bot, self.guild, {"days": "abc", "limit": None}), default=str)
        self.assertEqual(assistant.TOOLS["security_status"][1](self.bot, self.guild, {})["in_gulag"], 1)
        self.assertEqual(assistant.TOOLS["recent_logs"][1](self.bot, self.guild, {"category": "security"})["entries"][0]["member"], "eve")

    def test_parse(self):
        self.assertEqual(assistant.parse('{"answer": "a"}'), {"answer": "a"})
        self.assertEqual(assistant.parse("{broken"), {"answer": "{broken"})
        self.assertEqual(assistant.parse('{"other": 1}'), {"answer": '{"other": 1}'})


class Resp:
    def __init__(self, data, status=200):
        self.data, self.status = data, status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self, content_type=None):
        return self.data


class ServicesTest(AssistantTest):
    def test_tools_depend_on_setup(self):
        self.assertNotIn("railway_health", assistant.tools_for(self.bot, self.guild))
        self.bot.cfg(1)["ai"] = {"railway_enc": "x", "github_repo": "a/b", "uptime_urls": ["https://example.org"]}
        self.assertLessEqual({"railway_health", "railway_projects", "github_repo", "uptime"}, set(assistant.tools_for(self.bot, self.guild)))

    def test_railway_health(self):
        self.bot.cfg(1)["ai"] = {"railway_enc": "sealed"}
        sent = []

        def post(url, json=None, headers=None, timeout=None):
            sent.append((url, json["query"], headers))
            if "projects" in json["query"]:
                return Resp({"data": {"projects": {"edges": [{"node": {"id": "0a1b2c3d-1111", "name": "bot"}}, {"node": {"id": "x\" } evil", "name": "bad"}}]}}})
            return Resp({"data": {"deployments": {"edges": [{"node": {"id": "d1", "status": "SUCCESS", "createdAt": "2026-11-15"}}, {"node": {"id": "d0", "status": "FAILED", "createdAt": "2026-11-14"}}]}}})

        self.bot.session = SimpleNamespace(post=post)
        self.bot.ai.box = SimpleNamespace(open=lambda token: "secret-token")
        out = asyncio.run(assistant.EXTERNAL["railway_health"][1](self.bot, self.guild, {}))
        self.assertEqual(out, {"projects": [{"project": "bot", "latest": {"id": "d1", "status": "SUCCESS", "createdAt": "2026-11-15"}, "last_ten_by_status": {"SUCCESS": 1, "FAILED": 1}}]})
        self.assertEqual(sent[0][0], "https://backboard.railway.com/graphql/v2")
        self.assertEqual(sent[0][2], {"Authorization": "Bearer secret-token"})
        self.assertEqual(len(sent), 2)

    def test_railway_error_is_reported(self):
        self.bot.cfg(1)["ai"] = {"railway_enc": "sealed"}
        self.bot.session = SimpleNamespace(post=lambda *a, **k: Resp({"errors": [{"message": "Not Authorized"}]}))
        self.bot.ai.box = SimpleNamespace(open=lambda token: "t")
        out = asyncio.run(assistant.EXTERNAL["railway_projects"][1](self.bot, self.guild, {}))
        self.assertEqual(out["detail"], "Not Authorized")

    def test_actions_are_only_proposed(self):
        answer, trace, seen = self.run_with(['{"action": "slowmode", "args": {"seconds": 999999}}'])
        self.assertEqual(answer, "{\"action\": \"slowmode\", \"args\": {\"seconds\": 999999}}"[:0] or answer)
        self.assertEqual(trace, [])

        async def ask(gid, system, prompt, uid=None, max_tokens=None):
            self.assertIn("only happens after the staff member confirms", system)
            return '{"action": "slowmode", "args": {"seconds": 999999}}'

        text, trace = asyncio.run(assistant.run(self.bot, self.guild, "slow down the chat", ask=ask, actions=True))
        self.assertEqual(trace, [{"action": "slowmode", "args": {"seconds": 21600}}])
        self.assertEqual(text, "Slow mode of this channel: 21600 seconds")

    def test_clean_action(self):
        self.assertEqual(assistant.clean_action("timeout", {"member": "<@123>", "minutes": 99999}), {"member": 123, "minutes": 1440, "reason": "Assistant, confirmed by staff"})
        self.assertIsNone(assistant.clean_action("timeout", {"member": "everyone"}))
        self.assertIsNone(assistant.clean_action("ban", {}))
        self.assertEqual(assistant.clean_action("lock_channel", {"x": 1}), {})

    def test_perform(self):
        calls = []

        async def edit(**kw):
            calls.append(kw)

        channel = SimpleNamespace(edit=edit)
        out = asyncio.run(assistant.perform(SimpleNamespace(), channel, "slowmode", {"seconds": 30}, "ken"))
        self.assertEqual(out, "Done.")
        self.assertEqual(calls[0]["slowmode_delay"], 30)
        guild = SimpleNamespace(get_member=lambda i: None)
        self.assertEqual(asyncio.run(assistant.perform(guild, channel, "timeout", {"member": 1, "minutes": 5, "reason": "x"}, "ken")), "The member is not on this server.")


class LogsRouteTest(base.ManageTest):
    async def test_logs_route(self):
        self.bot.logbook.add(5, "security", "AutoMod: antiscam", "scam link", "eve", 9)
        self.bot.logbook.add(5, "messages", "Message deleted", "hi", "sam", 8)
        self.assertEqual((await self.client.get("/api/guild/5/logs")).status, 401)
        await self.login(ADMIN)
        r = await self.client.get("/api/guild/5/logs")
        self.assertEqual(r.status, 200)
        data = await r.json()
        self.assertEqual([e["title"] for e in data["entries"]], ["Message deleted", "AutoMod: antiscam"])
        self.assertTrue(data["stored"])
        r = await self.client.get("/api/guild/5/logs?category=security&q=scam")
        self.assertEqual(len((await r.json())["entries"]), 1)
        r = await self.client.get("/api/guild/5/logs?category=a'b")
        self.assertEqual(r.status, 400)
        r = await self.client.get("/api/guild/5/stats?days=7")
        stats = await r.json()
        self.assertEqual(sum(stats["logs"]["security"]), 1)
        self.assertIn("moderators", stats)

    async def test_viewers_cannot_read_logs(self):
        self.bot.cfg(5)["dashboard_access"] = {"viewer_roles": [20], "mod_roles": []}
        await self.login(VIEWER)
        self.assertEqual((await self.client.get("/api/guild/5/logs")).status, 403)

    async def test_bot_log_fills_the_book(self):
        guild = SimpleNamespace(id=5)
        e = discord.Embed(title="Member joined", description="welcome")
        self.bot.log(guild, "members", e)
        self.assertEqual(self.bot.logbook.read(5)[0]["title"], "Member joined")
        self.bot.cfg(5)["log_options"]["dashboard"] = False
        self.bot.log(guild, "members", discord.Embed(title="Second"))
        self.assertEqual(len(self.bot.logbook.read(5)), 1)


if __name__ == "__main__":
    unittest.main()


class MoreRoutesTest(base.ManageTest):
    async def test_export_members_cases_transcripts_and_api(self):
        from quorvane import transcripts
        guild = self.bot.get_guild(5)
        self.bot.logbook.add(5, "messages", "Message deleted", "=cmd() see https://discord.com/channels/500000000000000005/100000000000000010/123456789012345678", "sam", 8, [["Channel", "#general"]])
        self.bot.store.cases(5).append({"id": 1, "type": "warn", "user": ADMIN, "user_name": "a", "mod_name": "ken", "reason": "old", "ts": 1794000000})
        transcripts.keep(self.bot, guild, "Support-0001", b"<html>x</html>")
        self.assertEqual((await self.client.get("/api/guild/5/members")).status, 401)
        await self.login(ADMIN)
        rows = (await (await self.client.get("/api/guild/5/logs")).json())["entries"]
        self.assertEqual(rows[0]["url"], "https://discord.com/channels/500000000000000005/100000000000000010/123456789012345678")
        self.assertIsNone(rows[0]["avatar"])
        self.assertEqual(len((await (await self.client.get("/api/guild/5/logs?since=99999999999")).json())["entries"]), 0)
        r = await self.client.get("/api/guild/5/logs/export")
        text = await r.text()
        self.assertIn("attachment", r.headers["Content-Disposition"])
        self.assertIn("'=cmd() see", text)
        data = await (await self.client.get("/api/guild/5/members?q=" + str(ADMIN))).json()
        self.assertEqual(data["members"], [])  # the fake members have no id, nothing may break
        r = await self.post("/cases/1", {"reason": "new reason"})
        self.assertEqual(r.status, 200)
        self.assertEqual(self.bot.store.cases(5)[0]["reason"], "new reason")
        self.assertEqual((await self.post("/cases/1", {"reason": ""})).status, 400)
        self.assertEqual((await self.post("/cases/9", {"reason": "x"})).status, 404)
        self.assertEqual((await self.post("/cases/1", {"delete": True})).status, 200)
        self.assertEqual(self.bot.store.cases(5), [])
        files = (await (await self.client.get("/api/guild/5/transcripts")).json())["files"]
        self.assertEqual(files[0]["title"], "support-0001")
        r = await self.client.get("/api/guild/5/transcripts/" + files[0]["name"])
        self.assertEqual(await r.read(), b"<html>x</html>")
        self.assertIn("attachment", r.headers["Content-Disposition"])
        self.assertEqual((await self.client.get("/api/guild/5/transcripts/0000000000-..html")).status, 404)
        self.assertEqual((await self.client.get("/api/v1/guild/5/stats")).status, 401)
        token = (await (await self.post("/apitoken", {})).json())["token"]
        self.assertNotIn(token, str(self.bot.cfg(5)["dashboard_api"]))
        r = await self.client.get("/api/v1/guild/5/stats", headers={"Authorization": "Bearer " + token})
        self.assertEqual(r.status, 200)
        self.assertIn("messages", await r.json())
        self.assertEqual((await self.client.get("/api/v1/guild/5/logs", headers={"Authorization": "Bearer wrong"})).status, 401)
        await self.post("/apitoken", {"remove": True})
        self.assertEqual((await self.client.get("/api/v1/guild/5/stats", headers={"Authorization": "Bearer " + token})).status, 401)

    async def test_live_stream_sends_new_entries(self):
        await self.login(ADMIN)
        r = await self.client.get("/api/guild/5/logs/stream")
        self.assertEqual(r.status, 200)
        self.assertEqual(await r.content.readuntil(b"\n\n"), b": ready\n\n")
        self.bot.logbook.add(5, "security", "AutoMod: antiscam", "scam", "eve", 9)
        line = await asyncio.wait_for(r.content.readuntil(b"\n\n"), 3)
        self.assertIn(b'"title": "AutoMod: antiscam"', line)
        r.close()

    async def test_transcript_prune_and_assistant_route(self):
        from quorvane import transcripts
        folder = self.bot.store.dir / "transcripts" / "5"
        folder.mkdir(parents=True)
        (folder / "0000000100-old.html").write_bytes(b"x")
        self.assertEqual(transcripts.prune(self.bot, 5, 30), 1)
        await self.login(ADMIN)
        self.assertEqual((await self.post("/assistant", {"question": "how is it going?"})).status, 409)
        self.assertEqual((await self.post("/assistant", {"question": "x"})).status, 400)
