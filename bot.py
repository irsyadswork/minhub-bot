"""Minhub - bot Discord Clipper Hub Circle. Jalankan: python bot.py"""
import asyncio
import logging
import os
import random
import re
import time

import discord
from discord.ext import tasks
from dotenv import load_dotenv

import config
from ai import Brain
from campaigns import CampaignWatcher
from welcome_card import make_welcome_card

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("minhub")

intents = discord.Intents.default()
intents.members = True
# Message Content Intent nggak perlu: Discord tetap kasih isi pesan yang nge-tag bot.
client = discord.Client(intents=intents)

with open(os.path.join(HERE, "faq.md"), encoding="utf-8") as f:
    brain = Brain(os.environ["GEMINI_API_KEY"], f.read())
watcher = CampaignWatcher()

FALLBACK = "Waduh otakku lagi nge-lag bentar 😵‍💫 {admin} tolong bantu jawab yaa"


def find_channel(guild: discord.Guild, name: str):
    if not name:
        return None
    name = name.lower()
    channels = guild.text_channels
    return (next((c for c in channels if c.name.lower() == name), None)
            or next((c for c in channels if name in c.name.lower()), None))


def find_role(guild: discord.Guild, name: str):
    if not name:
        return None
    name = name.lower()
    return (next((r for r in guild.roles if r.name.lower() == name), None)
            or next((r for r in guild.roles if name in r.name.lower()), None))


def build_refs(guild: discord.Guild) -> tuple[dict, dict]:
    """Balikin (deskripsi untuk AI, placeholder -> mention asli)."""
    refs, mentions = {}, {}
    for key, desc, obj in [
        ("{brief}", "channel brief", find_channel(guild, config.BRIEF_CHANNEL)),
        ("{rules}", "channel rules", find_channel(guild, config.RULES_CHANNEL)),
        ("{admin}", "tim admin (tag mereka untuk bantu jawab)", find_role(guild, config.ADMIN_ROLE)),
    ]:
        if obj:
            refs[key] = desc
            mentions[key] = obj.mention
    return refs, mentions


def fill_mentions(text: str, mentions: dict) -> str:
    for key in ("{brief}", "{rules}", "{admin}"):
        text = text.replace(key, mentions.get(key, "admin" if key == "{admin}" else "channel tersebut"))
    return text.replace("@everyone", "everyone").replace("@here", "here")


def in_reply_channel(channel) -> bool:
    if not config.REPLY_CHANNELS:
        return True
    names = [channel.name.lower()]
    if getattr(channel, "parent", None):  # thread
        names.append(channel.parent.name.lower())
    return any(want.lower() in n for want in config.REPLY_CHANNELS for n in names)


@client.event
async def on_ready():
    log.info("Login sebagai %s di %d server", client.user, len(client.guilds))
    if not campaign_loop.is_running():
        campaign_loop.start()


@client.event
async def on_member_join(member: discord.Member):
    channel = find_channel(member.guild, config.WELCOME_CHANNEL)
    if not channel:
        log.warning("Channel welcome '%s' tidak ketemu", config.WELCOME_CHANNEL)
        return
    try:
        avatar = await member.display_avatar.replace(format="png", size=256).read()
        card = await asyncio.to_thread(make_welcome_card, avatar, member.name)
        await channel.send(
            config.WELCOME_TEXT.format(mention=member.mention, server=config.SERVER_NAME),
            file=discord.File(card, "welcome.png"),
            allowed_mentions=discord.AllowedMentions(users=True),
        )
    except Exception:
        log.exception("Gagal kirim welcome untuk %s", member)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    if client.user not in message.mentions or not in_reply_channel(message.channel):
        return

    question = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()
    if not question:
        question = "(cuma nge-tag kamu tanpa pertanyaan)"
    refs, mentions = build_refs(message.guild)

    # Jeda humanis: total 5-60 detik. Diam dulu sebentar ("baca"), lalu "typing..." sampai waktunya habis.
    total = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
    started = time.monotonic()
    answer = asyncio.create_task(
        brain.reply(question, message.author.display_name, refs, watcher.summary())
    )
    await asyncio.sleep(min(total * 0.3, random.uniform(2, 8)))

    async with message.channel.typing():
        try:
            result = await answer
            text = result["balasan"] or FALLBACK
            log.info("[%s] %s: %s", result["kategori"], message.author, question[:80])
        except Exception:
            log.exception("Gagal minta jawaban ke Gemini")
            text = FALLBACK
        remaining = total - (time.monotonic() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)

    await message.reply(
        fill_mentions(text, mentions)[:2000],
        allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False, replied_user=True),
    )


@tasks.loop(minutes=config.CAMPAIGN_CHECK_MINUTES)
async def campaign_loop():
    try:
        new = await watcher.check_new()
    except Exception:
        log.exception("Gagal cek campaign")
        return
    for c in new:
        for guild in client.guilds:
            channel = find_channel(guild, config.CAMPAIGN_CHANNEL)
            if not channel:
                log.warning("Channel campaign '%s' tidak ketemu di %s", config.CAMPAIGN_CHANNEL, guild)
                continue
            text, embed = watcher.announcement(c)
            await channel.send(text, embed=embed)
            log.info("Umumkan campaign baru: %s", c["slug"])


if __name__ == "__main__":
    client.run(os.environ["DISCORD_TOKEN"], log_handler=None)
