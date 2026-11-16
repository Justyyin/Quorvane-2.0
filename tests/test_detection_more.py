"""QR codes, linked images, the IP logger list, the shared scammer list and the migration to the gulag."""

import tempfile
import time
import unittest
from types import SimpleNamespace

from quorvane import migrations, qrscan, scamlinks
from quorvane.cogs.security import antiscam
from quorvane.metrics import Metrics
from tests import test_scamlinks as base


def qr_png(text):
    import cv2
    code = cv2.QRCodeEncoder.create().encode(text)
    big = cv2.copyMakeBorder(cv2.resize(code, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST), 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
    return cv2.imencode(".png", big)[1].tobytes()


class PureTest(unittest.TestCase):
    @unittest.skipUnless(qrscan.available(), "OpenCV is not installed")
    def test_qr_decode(self):
        self.assertEqual(qrscan.decode(qr_png("https://grabify.link/ABC")), ["https://grabify.link/ABC"])
        self.assertEqual(qrscan.decode(b"not an image"), [])
        self.assertEqual(qrscan.decode(b""), [])

    def test_parse_list(self):
        text = "# comment\ngrabber.example\n0.0.0.0 tracker.example # note\nhttps://Evil.Example/path\n*.wild.example\nnot a domain!\ndiscord.com\n\n"
        self.assertEqual(scamlinks.parse_list(text), {"grabber.example", "tracker.example", "evil.example", "wild.example"})
        self.assertEqual(len(scamlinks.parse_list("\n".join(f"a{i}.example" for i in range(50)), limit=10)), 10)

    def test_extra_list_is_used(self):
        scamlinks.EXTRA.add("fresh-logger.example")
        try:
            self.assertEqual(scamlinks.logger_host(["x.fresh-logger.example"]), "x.fresh-logger.example")
        finally:
            scamlinks.EXTRA.clear()

    def test_migration_moves_delete_to_jail(self):
        store = SimpleNamespace(config={1: {"antiscam": {"action": "delete"}}, 2: {"antiscam": {"action": "timeout"}}, 3: {}}, t_cfg=set())
        migrations.v4_scam_to_gulag(store)
        self.assertEqual(store.config[1]["antiscam"]["action"], "jail")
        self.assertEqual(store.config[2]["antiscam"]["action"], "timeout")
        self.assertEqual(store.t_cfg, {1})
        self.assertEqual(migrations.SCHEMA_VERSION, 4)

    def test_check_times(self):
        m = Metrics()
        m.check("scam_links", 0.001)
        m.check("scam_links", 0.003)
        self.assertEqual(m.check_times(), {"scam_links": {"count": 2, "avg_ms": 2.0, "max_ms": 3.0}})


class CogTest(base.CogTest):
    @unittest.skipUnless(qrscan.available(), "OpenCV is not installed")
    async def test_qr_code_with_ip_logger_is_removed(self):
        data = qr_png("https://grabify.link/ABC")

        async def read():
            return data

        att = SimpleNamespace(size=len(data), filename="code.png", content_type="image/png", url="https://cdn.discordapp.com/x.png", read=read, to_file=read)
        m = self.msg("scan this", attachments=[att])
        await self.cog.check(m)
        self.assertTrue(m.deleted)
        self.assertIn("QR code that leads to grabify.link", self.jailed[0][1])

    @unittest.skipUnless(qrscan.available(), "OpenCV is not installed")
    async def test_linked_image_is_checked(self):
        data = qr_png("https://dlscord.com/gift")
        seen = []

        class Resp:
            status = 200
            content = SimpleNamespace(read=None)

            async def __aenter__(self):
                async def read(n):
                    return data
                self.content = SimpleNamespace(read=read)
                return self

            async def __aexit__(self, *a):
                return False

        self.bot.session = SimpleNamespace(get=lambda url, timeout=None: seen.append(url) or Resp())
        m = self.msg("look")
        m.embeds = [SimpleNamespace(url=None, description=None, title=None, author=None, footer=None, fields=[], image=SimpleNamespace(proxy_url="https://media.discordapp.net/external/abc/pic.png"), thumbnail=SimpleNamespace(proxy_url="https://evil.example/pic.png"))]
        await self.cog.check(m)
        self.bot.session = None
        self.assertEqual(seen, ["https://media.discordapp.net/external/abc/pic.png"])
        self.assertTrue(m.deleted)

    async def test_shared_list(self):
        self.c["shared"]["enabled"] = True
        await self.cog.check(self.msg("https://dlscord.com/gift/abc"))
        self.assertIn("5", self.cog.shared_list())
        member = SimpleNamespace(id=5, bot=False, mention="<@5>", guild=SimpleNamespace(id=2, me=SimpleNamespace(id=999)))
        other = self.cog.conf(2)
        await self.cog.on_member_join(member)
        self.assertEqual(self.logs, [l for l in self.logs if l[1] != "Known scam account joined"])
        other["shared"].update(enabled=True, action="jail")
        before = len(self.jailed)
        await self.cog.on_member_join(member)
        self.assertIn(("security", "Known scam account joined"), self.logs)
        self.assertEqual(len(self.jailed), before + 1)

    async def test_shared_list_is_opt_in_and_expires(self):
        await self.cog.check(self.msg("https://dlscord.com/gift/abc"))
        self.assertEqual(self.cog.shared_list(), {})
        self.bot.store.set_state("scam_users", {"7": [int(time.time()) - 91 * 86400, "old"], "8": [int(time.time()), "new"]})
        self.assertEqual(list(self.cog.shared_list()), ["8"])


del base  # the tests of the base class run in their own module


class LinkedTest(unittest.TestCase):
    def test_proxy_hosts(self):
        self.assertIn("media.discordapp.net", antiscam.PROXY_HOSTS)
        self.assertEqual(antiscam.Linked(None, "https://media.discordapp.net/a/b.png").filename, "b.png")
        self.assertTrue(tempfile.gettempdir())
