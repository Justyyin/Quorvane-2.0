"""The HTML transcript of tickets and mod-mail."""

import asyncio
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from quorvane import i18n, transcripts

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def doc(**extra):
    base = {
        "kind": "ticket", "title": "Ticket 0012", "file": "support-0012", "subtitle": "Server · Support",
        "props": [("opened by", ("Sam", "sam.notes")), ("opened", 1794000000), ("reason", "Fixed <b>")],
        "quote": "It is gone", "history": [(1794000000, "Opened", "Sam", ""), (1794000300, "Closed", "Ken", "Fixed")],
        "notes": [(1794000100, "Ken", "internal only")],
        "messages": [{"name": "Sam", "handle": "sam.notes", "staff": False, "ts": 1794000050, "text": "<script>alert(1)</script> see https://example.org/a?b=1&c=2", "avatar": None, "files": []}],
    }
    base.update(extra)
    return base


class Asset:
    def __init__(self, data):
        self.data = data

    def replace(self, **_):
        return self

    async def read(self):
        if self.data is None:
            raise OSError("offline")
        return self.data


class RenderTest(unittest.TestCase):
    def test_member_text_is_escaped(self):
        page = transcripts.render(doc()).decode("utf-8")
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("Fixed &lt;b&gt;", page)
        self.assertIn('<a href="https://example.org/a?b=1&amp;c=2" rel="noopener noreferrer">', page)

    def test_policy_forbids_scripts_and_the_network(self):
        page = transcripts.render(doc()).decode("utf-8")
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'; img-src data:", page)
        self.assertNotIn("<script", page)
        self.assertNotIn('src="http', page)

    def test_staff_notes_only_in_the_staff_copy(self):
        self.assertIn("internal only", transcripts.render(doc(), staff_view=True).decode("utf-8"))
        self.assertNotIn("internal only", transcripts.render(doc(), staff_view=False).decode("utf-8"))

    def test_layout_parts(self):
        page = transcripts.render(doc(logo=transcripts.data_uri(PNG, 100))).decode("utf-8")
        for part in ('<div class="bar"><i></i><i></i><i></i>', "support-0012.html", "<h1>Ticket 0012</h1>", '<dl class="props">', "<blockquote>It is gone</blockquote>", '<ul class="log">', '<span class="av">S</span>', "2026-11-06"):
            self.assertIn(part, page)

    def test_accent_only_as_a_colour(self):
        self.assertIn("--gold:#112233", transcripts.render(doc(accent="#112233")).decode("utf-8"))
        self.assertIn("--gold:#dcc08a", transcripts.render(doc(accent="red;}</style>")).decode("utf-8"))

    def test_every_language(self):
        for lang in i18n.LANGUAGES:
            page = transcripts.render(doc(), lang).decode("utf-8")
            self.assertIn(i18n.tr(lang, "Conversation"), page)
            if lang != "en":
                for text in transcripts.TEXTS:
                    self.assertIn(text, i18n.table(lang), f"{lang}: {text}")

    def test_modmail_footer(self):
        self.assertIn("conversation closed", transcripts.render(doc(kind="modmail")).decode("utf-8"))

    def test_data_uri(self):
        self.assertTrue(transcripts.data_uri(PNG, 100).startswith("data:image/png;base64,"))
        self.assertIsNone(transcripts.data_uri(b"<svg onload=x>", 100))
        self.assertIsNone(transcripts.data_uri(PNG, 10))
        self.assertIsNone(transcripts.data_uri(None, 10))


class CollectTest(unittest.TestCase):
    def setUp(self):
        self.sam = SimpleNamespace(id=2, name="sam.notes", display_name="Sam", bot=False, display_avatar=Asset(PNG))
        self.ken = SimpleNamespace(id=3, name="ken", display_name="Ken", bot=False, display_avatar=Asset(None))
        self.guild = SimpleNamespace(
            id=1, icon=Asset(PNG), banner=None,
            get_member=lambda i: {2: self.sam, 3: self.ken}.get(i), get_role=lambda i: SimpleNamespace(name="Support") if i == 77777 else None,
            get_channel=lambda i: SimpleNamespace(name="rules") if i == 88888 else None,
        )

    def channel(self, messages):
        async def history(limit=None, oldest_first=True):
            for m in messages:
                yield m
        return SimpleNamespace(guild=self.guild, history=history)

    def message(self, author, content, attachments=(), embeds=()):
        return SimpleNamespace(author=author, content=content, attachments=list(attachments), embeds=list(embeds), created_at=datetime(2026, 11, 6, 4, 5, tzinfo=timezone.utc))

    def test_conversation(self):
        big = SimpleNamespace(filename="video.mp4", content_type="video/mp4", size=9_000_000, read=None)
        shot = SimpleNamespace(filename="shot.png", content_type="image/png", size=len(PNG), read=Asset(PNG).read)
        ch = self.channel([
            self.message(self.sam, "hi <@00003> in <#88888> for <@&77777> and <@99999>", [shot, big]),
            self.message(self.ken, ""),
            self.message(self.ken, "", embeds=[SimpleNamespace(title="Ticket claimed", description="Ken takes care")]),
        ])
        out = asyncio.run(transcripts.conversation(ch, lambda u: u.id == 3))
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["text"], "hi @Ken in #rules for @Support and <@99999>")
        self.assertFalse(out[0]["staff"])
        self.assertTrue(out[0]["avatar"].startswith("data:image/png"))
        self.assertTrue(out[0]["files"][0]["image"].startswith("data:image/png"))
        self.assertIsNone(out[0]["files"][1]["image"])
        self.assertTrue(out[1]["staff"])
        self.assertIsNone(out[1]["avatar"])
        self.assertEqual(out[1]["text"], "Ticket claimed\nKen takes care")
        page = transcripts.render({"title": "T", "messages": out}).decode("utf-8")
        self.assertIn("video.mp4", page)

    def test_dress(self):
        bot = SimpleNamespace(cfg=lambda gid: {"look": {"accent": "#abcdef"}})
        out = asyncio.run(transcripts.dress({}, bot, self.guild))
        self.assertTrue(out["logo"].startswith("data:image/png"))
        self.assertIsNone(out["banner"])
        self.assertEqual(out["accent"], "#abcdef")


if __name__ == "__main__":
    unittest.main()
