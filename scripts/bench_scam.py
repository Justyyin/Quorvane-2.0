"""Measure how fast the anti-scam check handles messages. Run: python scripts/bench_scam.py [messages]

It starts the real bot without a connection, feeds it harmless and scam messages and prints messages per second and the time per check.
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quorvane.core import EXTENSIONS, Bot  # noqa: E402

TEXTS = ("good morning everyone", "has anyone seen the new patch notes? https://example.org/notes", "lol that was a great round",
         "free nitro for all https://dlscord.com/gift/abc", "look https://grabify.link/ABC123", "MrBeast giveaway, claim your BTC now")


async def main(count: int) -> None:
    bot = Bot({"data_dir": tempfile.mkdtemp()})

    async def never_ready():
        await asyncio.Event().wait()

    bot.wait_until_ready = never_ready
    for ext in EXTENSIONS:
        await bot.load_extension(f"quorvane.cogs.{ext}")
    cog, automod = bot.get_cog("AntiScam"), bot.get_cog("AutoMod")
    bot.module_on = lambda gid, name: True
    automod.exempt = lambda msg, a: False
    automod.excepted = lambda msg, rule: False

    async def act(msg, rule, reason, action, fast=False):
        return None

    async def remove(msg, reason, notify=True, fast=False):
        return True

    automod.act, automod.remove = act, remove
    cog.conf(1)["images"] = False
    guild = SimpleNamespace(id=1, me=SimpleNamespace(id=9), name="bench")

    async def nothing(*a, **k):
        return None

    messages = [SimpleNamespace(id=i, guild=guild, author=SimpleNamespace(id=100 + i % 500, bot=False), content=TEXTS[i % len(TEXTS)], attachments=[], embeds=[],
                                message_snapshots=[], stickers=[], channel=SimpleNamespace(id=7), delete=nothing) for i in range(count)]
    start = time.perf_counter()
    for m in messages:
        await cog.check(m)
    took = time.perf_counter() - start
    print(f"{count} messages in {took:.2f} s, {count / took:.0f} per second, {took / count * 1000:.3f} ms each")
    for name, row in sorted(bot.metrics.check_times().items()):
        print(f"  {name:14} {row['count']:>7} runs  avg {row['avg_ms']:.3f} ms  slowest {row['max_ms']:.3f} ms")
    for name in list(bot.cogs):
        await bot.remove_cog(name)
    bot.store.close()
    bot.logbook.close()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 20000))
