"""Channel tools: a thread under every message, channels for pictures and links only, publishing announcements, and solved forum posts."""

import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from ... import i18n
from ...cog import BaseCog

log = logging.getLogger(__name__)

LINK = re.compile(r"https?://\S+")


def thread_name(text: str, author: str) -> str:
    """A name for the thread of a message: its first line, or the name of the author."""
    first = re.sub(r"\s+", " ", (text or "").strip().split("\n", 1)[0])
    first = LINK.sub("", first).strip()
    return (first or author)[:80]


class ChannelTools(BaseCog):
    """Small automatic helpers for single channels."""

    section = "channeltools"

    def staff(self, member) -> bool:
        """Members who may always write: everyone with Manage Messages."""
        perms = getattr(member, "guild_permissions", None)
        return bool(perms and perms.manage_messages)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """Apply the rules of the channel to a new message."""
        if msg.guild is None or not self.bot.module_on(msg.guild.id, "channeltools"):
            return
        c = self.conf(msg.guild.id)
        cid = msg.channel.id
        if cid in c["publish"] and getattr(msg.channel, "type", None) == discord.ChannelType.news and not msg.flags.crossposted:
            try:
                await msg.publish()
            except discord.HTTPException as exc:
                log.info("message could not be published: %s", exc)
        if msg.author.bot:
            return
        if cid in c["media_only"] and not self.staff(msg.author) and not (msg.attachments or LINK.search(msg.content or "") or msg.embeds):
            try:
                await msg.delete()
                await msg.channel.send(i18n.say(self.bot, msg.guild, "{user}, this channel is for pictures and links only.", user=msg.author.mention), delete_after=8,
                                       allowed_mentions=discord.AllowedMentions(users=[msg.author]))
            except discord.HTTPException as exc:
                log.info("media-only message could not be removed: %s", exc)
            return
        if cid in c["threads"] and isinstance(msg.channel, discord.TextChannel):
            try:
                await msg.create_thread(name=thread_name(msg.content, msg.author.display_name), auto_archive_duration=c["archive_minutes"] if c["archive_minutes"] in (60, 1440, 4320, 10080) else 1440)
            except discord.HTTPException as exc:
                log.info("thread could not be created: %s", exc)

    @commands.hybrid_command(name="solved", description="Mark this forum post as solved and close it")
    @commands.guild_only()
    async def solved(self, ctx) -> None:
        """The author of a forum post or the staff close it. A tag named like the setting is added when the forum has one."""
        thread = ctx.channel
        if not isinstance(thread, discord.Thread) or not isinstance(thread.parent, discord.ForumChannel):
            return await ctx.send(i18n.say(self.bot, ctx.guild, "Use this inside a forum post."), ephemeral=True)
        if ctx.author.id != thread.owner_id and not self.staff(ctx.author):
            return await ctx.send(i18n.say(self.bot, ctx.guild, "Only the author of the post or the staff can close it."), ephemeral=True)
        wanted = self.conf(ctx.guild.id)["solved_tag"].casefold()
        tag = next((t for t in thread.parent.available_tags if t.name.casefold() == wanted), None)
        tags = list(thread.applied_tags)
        if tag and tag not in tags:
            tags = (tags + [tag])[-5:]
        await ctx.send(i18n.say(self.bot, ctx.guild, "Marked as solved. The post is closed."))
        try:
            await thread.edit(applied_tags=tags, archived=True, locked=True, reason=f"Solved, closed by {ctx.author}")
        except discord.HTTPException as exc:
            log.warning("forum post could not be closed: %s", exc)


async def setup(bot) -> None:
    """Register the cog with the bot."""
    await bot.add_cog(ChannelTools(bot))


__all__ = ["ChannelTools", "thread_name", "app_commands"]
