"""Channel tools, the welcome picture and the counters behind the new charts."""

import asyncio
import copy
import unittest
from types import SimpleNamespace

import discord

from quorvane import images
from quorvane.cogs.community import channeltools
from quorvane.defaults import DEFAULTS


class Message:
    def __init__(self, cid, content="", attachments=(), bot=False, staff=False, kind=discord.ChannelType.text):
        self.calls = []
        self.guild = SimpleNamespace(id=1)
        self.content, self.attachments, self.embeds = content, list(attachments), []
        self.author = SimpleNamespace(bot=bot, mention="<@5>", display_name="Sam", guild_permissions=SimpleNamespace(manage_messages=staff))
        self.flags = SimpleNamespace(crossposted=False)
        channel = discord.Object(id=cid)
        channel.type = kind
        channel.send = self.record("send")
        self.channel = channel
        self.delete, self.publish, self.create_thread = self.record("delete"), self.record("publish"), self.record("thread")

    def record(self, name):
        async def call(*a, **k):
            self.calls.append((name, k.get("name")))
        return call


class ChannelToolsTest(unittest.TestCase):
    def setUp(self):
        self.cfg = copy.deepcopy(DEFAULTS)
        self.cfg["channeltools"].update(threads=[10], media_only=[20], publish=[30])
        bot = SimpleNamespace(cfg=lambda gid: self.cfg, module_on=lambda gid, name: self.on, lang_of=lambda g: "en")
        self.on = True
        self.cog = channeltools.ChannelTools(bot)

    def run_message(self, m):
        asyncio.run(self.cog.on_message(m))
        return [c[0] for c in m.calls]

    def test_thread_name(self):
        self.assertEqual(channeltools.thread_name("  My   idea\nmore text", "Sam"), "My idea")
        self.assertEqual(channeltools.thread_name("https://example.org/x", "Sam"), "Sam")
        self.assertEqual(len(channeltools.thread_name("x" * 300, "Sam")), 80)

    def test_media_only(self):
        self.assertEqual(self.run_message(Message(20, "just talking")), ["delete", "send"])
        self.assertEqual(self.run_message(Message(20, "look https://example.org/a.png")), [])
        self.assertEqual(self.run_message(Message(20, "", attachments=["file"])), [])
        self.assertEqual(self.run_message(Message(20, "staff may talk", staff=True)), [])

    def test_publish(self):
        self.assertEqual(self.run_message(Message(30, "news", bot=True, kind=discord.ChannelType.news)), ["publish"])
        self.assertEqual(self.run_message(Message(30, "news", kind=discord.ChannelType.text)), [])

    def test_module_switch(self):
        self.on = False
        self.assertEqual(self.run_message(Message(20, "just talking")), [])

    def test_defaults(self):
        self.assertFalse(DEFAULTS["modules"]["channeltools"])
        self.assertEqual(DEFAULTS["channeltools"]["solved_tag"], "Solved")
        self.assertFalse(DEFAULTS["welcome"]["picture"])


class PictureTest(unittest.TestCase):
    def test_welcome_card(self):
        data = images.welcome_card("Sam", b"not an image", "Lautre", 120)
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertGreater(len(data), 2000)


if __name__ == "__main__":
    unittest.main()
