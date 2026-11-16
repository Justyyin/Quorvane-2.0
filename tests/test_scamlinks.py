"""Scam links: IP loggers, domains that imitate Discord or Steam, and what the anti-scam cog does with them."""

import asyncio
import tempfile
import time
import unittest
from types import SimpleNamespace

from quorvane import scamlinks
from quorvane.cogs.security import antiscam
from quorvane.core import EXTENSIONS, Bot


class HostTest(unittest.TestCase):
    def test_ip_loggers(self):
        self.assertEqual(scamlinks.logger_host(["example.org", "www.Grabify.link"]), "www.grabify.link")
        for host in ("iplogger.org", "2no.co", "yip.su", "a.b.iplogger.com"):
            self.assertEqual(scamlinks.logger_host([host]), host)
        self.assertIsNone(scamlinks.logger_host(["github.com", "notgrabify.link", "discord.com"]))
        self.assertEqual(scamlinks.logger_host(["track.example.io"], extra=["Example.io"]), "track.example.io")
        self.assertIsNone(scamlinks.logger_host(["grabify.link"], allow=["grabify.link"]))

    def test_imitations_are_found(self):
        for host in ("dlscord.com", "discrod.gift", "disc0rd.gg", "d1scord.com", "dicord.gg", "discord-nitro.example.ru", "discord.gift-claim.ru",
                     "steamcommunlty.com", "stearncommunity.ru", "steamcommunity.com.ru", "dlscord.co.uk", "discordapp.co"):
            self.assertEqual(scamlinks.fake_host([host]), host, host)

    def test_real_sites_stay(self):
        for host in ("discord.com", "cdn.discordapp.com", "media.discordapp.net", "discord.gg", "store.steampowered.com", "steamcommunity.com", "discord.js.org",
                     "discordpy.readthedocs.io", "discord.me", "disboard.org", "discourse.org", "record.com", "top.gg", "steamdb.info", "github.com", "192.168.1.1", "localhost"):
            self.assertIsNone(scamlinks.fake_host([host]), host)
        self.assertIsNone(scamlinks.fake_host(["dlscord.com"], allow=["dlscord.com"]))

    def test_distance(self):
        self.assertEqual(scamlinks.distance("discord", "discord"), 0)
        self.assertEqual(scamlinks.distance("discrod", "discord"), 1)
        self.assertEqual(scamlinks.distance("dscord", "discord"), 1)
        self.assertGreater(scamlinks.distance("google", "discord"), 2)


class Message:
    """A message that remembers whether it was deleted."""
    count = 100

    def __init__(self, guild, author, content, channel=None, attachments=(), snapshots=()):
        Message.count += 1
        self.id, self.guild, self.author, self.content = Message.count, guild, author, content
        self.attachments, self.embeds, self.message_snapshots, self.stickers = list(attachments), [], list(snapshots), []
        self.channel = channel or SimpleNamespace(id=7, mention="#c", send=self.nothing)
        self.jump_url, self.deleted, self.deleted_at = "https://discord.com/x", False, None

    async def nothing(self, *a, **k):
        return None

    async def delete(self):
        self.deleted, self.deleted_at = True, time.perf_counter()


class CogTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = Bot({"data_dir": tempfile.mkdtemp()})

        async def never_ready():
            await asyncio.Event().wait()

        self.bot.wait_until_ready = never_ready
        for ext in EXTENSIONS:
            await self.bot.load_extension(f"quorvane.cogs.{ext}")
        self.bot.loop = asyncio.get_running_loop()
        self.cog = self.bot.get_cog("AntiScam")
        self.automod = self.bot.get_cog("AutoMod")
        self.c = self.cog.conf(1)
        self.jailed, self.timeouts, self.logs = [], [], []

        async def send_to_jail(member, moderator, reason=None, auto=False, **_):
            self.jailed.append((member.id, reason))
            return True, "ok"

        self.bot.get_cog("Jail").send_to_jail = send_to_jail
        self.bot.log = lambda guild, kind, e, files=None: self.logs.append((kind, e.title))
        self.automod.exempt = lambda msg, a: False
        self.automod.excepted = lambda msg, rule: False
        self.guild = SimpleNamespace(id=1, me=SimpleNamespace(id=999), name="G")
        self.bot.module_on = lambda gid, name: True

        async def timeout(delta, reason=None):
            self.timeouts.append(delta)

        self.user = SimpleNamespace(id=5, bot=False, mention="<@5>", display_avatar=SimpleNamespace(url="https://cdn.discordapp.com/a.png"), timeout=timeout, __str__=lambda s: "u")

    async def asyncTearDown(self):
        for cog in list(self.bot.cogs):
            await self.bot.remove_cog(cog)
        await asyncio.sleep(0)
        self.bot.store.close()

    def msg(self, content, **kw):
        return Message(self.guild, self.user, content, **kw)

    def test_defaults(self):
        self.assertEqual(self.c["action"], "jail")
        self.assertTrue(self.c["links"])
        self.assertTrue(self.c["purge"])
        self.assertEqual(self.c["iplogger"], {"enabled": True, "action": "delete", "domains": [], "allow": []})

    async def test_ip_logger_is_deleted_and_nobody_is_jailed(self):
        m = self.msg("look at this https://grabify.link/ABC123")
        await self.cog.check(m)
        self.assertTrue(m.deleted)
        self.assertEqual(self.jailed, [])
        self.c["iplogger"]["action"] = "jail"
        await self.cog.check(self.msg("https://iplogger.org/2x"))
        self.assertEqual(len(self.jailed), 1)

    async def test_ip_logger_switch_and_allow_list(self):
        self.c["iplogger"]["enabled"] = False
        m = self.msg("https://grabify.link/ABC123")
        await self.cog.check(m)
        self.assertFalse(m.deleted)
        self.c["iplogger"].update(enabled=True, allow=["grabify.link"])
        await self.cog.check(m)
        self.assertFalse(m.deleted)

    async def test_fake_link_deletes_and_sends_to_the_gulag(self):
        m = self.msg("free nitro for everyone https://dlscord.com/gift/abc")
        await self.cog.check(m)
        self.assertTrue(m.deleted)
        self.assertEqual(self.jailed[0][0], 5)
        self.assertIn("imitates Discord or Steam", self.jailed[0][1])

    async def test_scam_text_goes_to_the_gulag_by_default(self):
        m = self.msg("MrBeast giveaway, claim your BTC now")
        await self.cog.check(m)
        self.assertTrue(m.deleted)
        self.assertEqual(len(self.jailed), 1)

    async def test_forwarded_scam_counts(self):
        m = self.msg("", snapshots=[SimpleNamespace(content="https://steamcommunlty.com/trade", attachments=[], embeds=[])])
        await self.cog.check(m)
        self.assertTrue(m.deleted)

    async def test_copies_in_other_channels_are_removed(self):
        text = "MrBeast giveaway, claim your BTC now"
        harmless = self.msg("good morning")
        other = self.msg("totally different words with a link https://example.org")
        self.c["text"] = False  # the first copies slip through, as when the scan was still running
        first, second = self.msg(text), self.msg(text)
        for m in (harmless, other, first, second):
            await self.cog.check(m)
        self.c["text"] = True
        last = self.msg(text)
        await self.cog.check(last)
        self.assertTrue(last.deleted and first.deleted and second.deleted and other.deleted)
        self.assertFalse(harmless.deleted)

    async def test_purge_can_be_switched_off(self):
        self.c["text"], self.c["purge"] = False, False
        first = self.msg("MrBeast giveaway, claim your BTC now")
        await self.cog.check(first)
        self.c["text"] = True
        await self.cog.check(self.msg("MrBeast giveaway, claim your BTC now"))
        self.assertFalse(first.deleted)

    async def test_log_only_keeps_the_message(self):
        self.c["action"] = "log"
        m = self.msg("https://dlscord.com/gift/abc")
        await self.cog.check(m)
        self.assertFalse(m.deleted)
        self.assertEqual(self.jailed, [])

    async def test_without_a_gulag_the_member_is_timed_out(self):
        async def no_jail(member, moderator, reason=None, auto=False, **_):
            return False, "The gulag is not set up. Run /access jailsetup setup first."

        self.bot.get_cog("Jail").send_to_jail = no_jail
        m = self.msg("https://dlscord.com/gift/abc")
        await self.cog.check(m)
        self.assertTrue(m.deleted)
        self.assertEqual(self.timeouts[0].total_seconds(), 3600)

    async def test_delete_does_not_wait_for_the_log_copy(self):
        """The message is gone while its file is still being copied for the log."""
        done = {}

        class Slow:
            size, filename, content_type, url = 10, "a.png", "image/png", "https://cdn.discordapp.com/a.png"

            async def to_file(self):
                await asyncio.sleep(0.2)
                done["at"] = time.perf_counter()
                return None

            async def read(self):
                return b"x"

        self.c["images"] = False
        m = self.msg("https://grabify.link/ABC123", attachments=[Slow()])
        await self.cog.check(m)
        self.assertTrue(m.deleted)
        self.assertLess(m.deleted_at, done["at"])

    async def test_slow_second_opinion_does_not_hold_back_the_pictures(self):
        async def slow(msg, c, v, full):
            await asyncio.sleep(5)

        async def quick(msg, c):
            return "scam image already known as scam"

        self.cog.second_look, self.cog.images_verdict = slow, quick
        m = self.msg("hello there")
        start = time.perf_counter()
        await self.cog.check(m)
        self.assertTrue(m.deleted)
        self.assertLess(time.perf_counter() - start, 1)

    def test_link_check_is_fast(self):
        m = self.msg("some text https://example.org/a https://dlscord.com/x " * 5)
        start = time.perf_counter()
        for _ in range(300):
            self.cog.link_verdict(m, self.c)
        self.assertLess((time.perf_counter() - start) / 300, 0.002)


class PartsTest(unittest.TestCase):
    def test_hosts_of_text_forwards_and_embeds(self):
        snap = SimpleNamespace(content="see https://b.example", attachments=["f"], embeds=[SimpleNamespace(url="https://c.example/x", description="go to https://d.example")])
        m = SimpleNamespace(content="https://a.example", attachments=[], embeds=[], message_snapshots=[snap])
        self.assertEqual(antiscam.all_hosts(m), ["a.example", "b.example", "c.example", "d.example"])
        self.assertEqual(antiscam.all_files(m), ["f"])


if __name__ == "__main__":
    unittest.main()


class RenameTest(unittest.TestCase):
    def test_old_database_is_taken_over(self):
        from pathlib import Path
        from quorvane.store import Store
        folder = Path(tempfile.mkdtemp())
        first = Store(folder)
        first.cfg(1)["prefix"] = "?"
        first.mark("guilds") if hasattr(first, "mark") else None
        first.flush()
        first.close()
        (folder / "quorvane.db").rename(folder / "guardbot.db")
        second = Store(folder)
        self.assertFalse((folder / "guardbot.db").exists())
        self.assertTrue((folder / "quorvane.db").exists())
        second.close()
