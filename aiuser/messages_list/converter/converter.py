import logging

from discord import Message
from redbot.core import commands

from aiuser.abc import MixinMeta
from aiuser.common.constants import MAX_MESSAGE_LENGTH
from aiuser.common.utilities import contains_youtube_link, is_embed_valid
from aiuser.messages_list.converter.embed.formatter import format_embed_content
from aiuser.messages_list.converter.helpers import (format_embed_text_content,
                                                    format_sticker_content,
                                                    format_text_content)
from aiuser.messages_list.converter.image.caption import transcribe_image
from aiuser.messages_list.entry import MessageEntry

logger = logging.getLogger("red.bz_cogs.aiuser")


class MessageConverter():
    def __init__(self, cog: MixinMeta, ctx: commands.Context):
        self.cog = cog
        self.config = cog.config
        self.bot_id = cog.bot.user.id
        self.init_msg_id = ctx.message.id
        self.message_cache = cog.cached_messages
        self.ctx = ctx

    async def convert(self, message: Message):
        """Converts a Discord message to ChatML format message(s)"""
        res = []
        role = "user" if message.author.id != self.bot_id else "assistant"
        if message.attachments:
            await self.handle_attachment(message, res, role)
        elif message.stickers:
            content = format_sticker_content(message)
            await self.add_entry(content, res, role)
        elif (len(message.embeds) > 0 and is_embed_valid(message)) or contains_youtube_link(message.content):
            await self.handle_embed(message, res, role)
        else:
            content = format_text_content(message)
            await self.add_entry(content, res, role)

        return res or None

    async def handle_attachment(self, message: Message, res, role):
        if not message.attachments[0].content_type.startswith('image/'):
            content = f'User "{message.author.display_name}" sent: [Attachment: "{message.attachments[0].filename}"]'
            await self.add_entry(content, res, role)
        elif message.attachments[0].size > await self.config.guild(message.guild).max_image_size():
            content = f'User "{message.author.display_name}" sent: [Image: "{message.attachments[0].filename}"]'
            await self.add_entry(content, res, role)
        # scan only the triggering image
        elif self.init_msg_id == message.id and not self.ctx.interaction and await self.config.guild(message.guild).scan_images():
            content = await transcribe_image(self.cog, message) or f'User "{message.author.display_name}" sent: [Image: "{message.attachments[0].filename}"]'
            await self.add_entry(content, res, role)
        elif message.id in self.message_cache:
            await self.add_entry(self.message_cache[message.id], res, role)
        else:
            content = f'User "{message.author.display_name}" sent: [Image: "{message.attachments[0].filename}"]'
            await self.add_entry(content, res, role)

        content = format_text_content(message)
        await self.add_entry(content, res, role)

    async def handle_embed(self, message: Message, res, role):
        content = await format_embed_content(self.cog, message)
        if not content:
            content = format_text_content(message)
            await self.add_entry(content, res, role)
        else:
            await self.add_entry(content, res, role)
            content = format_embed_text_content(message)
            await self.add_entry(content, res, role)

    async def add_entry(self, content, res, role):
        if not content:
            return
        if (len(content.split())) > MAX_MESSAGE_LENGTH:
            role = "system"
            content = "A overly long message was omitted"
        res.append(MessageEntry(role, content))
