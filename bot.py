"""Minhub - bot Discord Clipper Hub Circle. Jalankan: python bot.py"""
import asyncio
import datetime
import json
import logging
import os
import random
import re
import time
import urllib.request

import discord
from discord.ext import tasks
from dotenv import load_dotenv

import config
from ai import Brain
from campaigns import CampaignWatcher
from viral import ViralSharer
from welcome_card import make_welcome_card

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("minhub")


def detect_intents(token: str) -> discord.Intents:
    """Pakai Message Content Intent kalau sudah dinyalakan di Developer Portal; kalau belum, bot tetap jalan
    tapi cuma bisa baca pesan yang nge-tag dia (fitur nimbrung otomatis mati)."""
    intents = discord.Intents.default()
    intents.members = True
    try:
        req = urllib.request.Request("https://discord.com/api/v10/applications/@me", headers={
            "Authorization": f"Bot {token}", "User-Agent": "DiscordBot (minhub, 1.0)"})
        flags = json.load(urllib.request.urlopen(req, timeout=15)).get("flags", 0)
        intents.message_content = bool(flags & ((1 << 18) | (1 << 19)))
    except Exception:
        log.exception("Gagal cek intent aplikasi")
    if not intents.message_content:
        log.warning("Message Content Intent belum aktif: Minhub cuma bisa jawab kalau di-tag.")
    return intents


client = discord.Client(intents=detect_intents(os.environ["DISCORD_TOKEN"]))

with open(os.path.join(HERE, "faq.md"), encoding="utf-8") as f:
    brain = Brain(os.environ["GEMINI_API_KEY"], f.read())
watcher = CampaignWatcher()
viral = ViralSharer()

FALLBACK = "Waduh otakku lagi nge-lag bentar 😵‍💫 {admin} tolong bantu jawab yaa"
QUESTION_HINT = re.compile(
    r"\?|\b(gimana|bagaimana|gmn|kapan|berapa|brp|apakah|apa|bisa|boleh|cara|kenapa|knp|kok|min|mimin|admin|"
    r"tanya|nanya|brief|cair|payout|bayar|transfer|withdraw|narik|views|deadline|hashtag|upload|aturan|rules|qc|"
    r"join|minimal|maksimal|bingung)\b")
last_auto_reply: dict[int, float] = {}
sync_lock = asyncio.Lock()


# ---------- helper channel & role ----------

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


def base_channel(channel):
    return channel.parent if isinstance(channel, discord.Thread) and channel.parent else channel


def is_admin(member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    role = find_role(member.guild, config.ADMIN_ROLE)
    return (role in member.roles) or member.guild_permissions.manage_guild


def campaign_channels(guild: discord.Guild) -> dict:
    """slug -> channel diskusi campaign (dikenali dari topic channel)."""
    found = {}
    for ch in guild.text_channels:
        slug = watcher.slug_from_topic(ch.topic)
        if slug:
            found[slug] = ch
    return found


def build_refs(guild: discord.Guild, campaign=None) -> tuple[dict, dict]:
    """Balikin (deskripsi untuk AI, placeholder -> teks asli)."""
    refs, mentions = {}, {}
    if campaign:
        refs["{brief}"] = "halaman brief campaign ini"
        mentions["{brief}"] = watcher.link(campaign)
    for key, desc, obj in [
        ("{rules}", "channel rules", find_channel(guild, config.RULES_CHANNEL)),
        ("{admin}", "tim admin (tag mereka untuk bantu jawab)", find_role(guild, config.ADMIN_ROLE)),
    ]:
        if obj:
            refs[key] = desc
            mentions[key] = obj.mention
    return refs, mentions


def fill_mentions(text: str, mentions: dict) -> str:
    for key in ("{brief}", "{rules}", "{admin}"):
        text = text.replace(key, mentions.get(key, "admin" if key == "{admin}" else "brief di website"))
    return text.replace("@everyone", "everyone").replace("@here", "here")


async def recent_history(message: discord.Message) -> str:
    lines = []
    try:
        async for m in message.channel.history(limit=config.HISTORY_MESSAGES, before=message):
            name = config.BOT_NAME if m.author == client.user else m.author.display_name
            text = m.clean_content[:300] or ("[kirim lampiran]" if m.attachments else "")
            lines.append(f"{name}: {text}")
    except discord.HTTPException:
        pass
    return "\n".join(reversed(lines))


# ---------- bot ngatur channel sendiri ----------

def public_overwrites(guild: discord.Guild) -> dict:
    return {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            add_reactions=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
    }


async def sync_guild(guild: discord.Guild):
    """Pastikan #diskusi, channel kontrol admin, dan channel diskusi tiap campaign aktif sudah ada."""
    async with sync_lock:
        try:
            if not find_channel(guild, config.GENERAL_CHANNEL):
                ch = await guild.create_text_channel(
                    config.GENERAL_CHANNEL, overwrites=public_overwrites(guild),
                    topic=f"Ngobrol bebas seputar clipping. {config.BOT_NAME} standby buat jawab pertanyaan.",
                    reason="Minhub: channel diskusi umum")
                log.info("Bikin channel #%s", ch.name)

            if not find_channel(guild, config.CONTROL_CHANNEL):
                admin = find_role(guild, config.ADMIN_ROLE)
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True,
                        attach_files=True, embed_links=True, add_reactions=True),
                }
                if admin:
                    overwrites[admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                                    attach_files=True, read_message_history=True)
                ch = await guild.create_text_channel(
                    config.CONTROL_CHANNEL, overwrites=overwrites,
                    topic=f"Channel privat admin: suruh {config.BOT_NAME} share info/screenshot ke channel campaign.",
                    reason="Minhub: channel kontrol admin")
                await ch.send(f"👋 Halo admin! Di sini kalian bisa nyuruh aku, contoh: kirim screenshot + "
                              f"*\"bro share ini ke grup siti si vampir, bilang ada angle baru\"*. "
                              f"Aku bakal kasih preview dulu, react ✅ buat kirim.")
                log.info("Bikin channel #%s", ch.name)

            existing = campaign_channels(guild)
            category = None
            for c in watcher.active():
                if c["slug"] in existing:
                    continue
                if category is None:
                    category = (discord.utils.find(lambda k: k.name.lower() == config.CAMPAIGN_CATEGORY.lower(),
                                                   guild.categories)
                                or await guild.create_category(config.CAMPAIGN_CATEGORY, reason="Minhub"))
                ch = await guild.create_text_channel(
                    watcher.channel_name(c), category=category, topic=watcher.channel_topic(c),
                    overwrites=public_overwrites(guild), reason=f"Minhub: diskusi campaign {c['slug']}")
                existing[c["slug"]] = ch
                log.info("Bikin channel #%s", ch.name)
        except discord.Forbidden:
            log.warning("Minhub belum punya izin Manage Channels / Manage Roles, channel nggak bisa dibuat otomatis")
            return

        for slug, ch in existing.items():
            c = watcher.get(slug)
            if c and ch.id not in intro_done:
                await ensure_intro(ch, c)


intro_done: set[int] = set()


async def ensure_intro(channel: discord.TextChannel, c: dict):
    """Pastikan pesan pembuka campaign ada, pakai banner, dan di-pin. Pesan lama milik Minhub di-update."""
    text, embed = watcher.intro(c)
    msg = None
    try:
        async for m in channel.history(limit=30, oldest_first=True):
            if m.author == client.user and m.content.startswith("👋 Ini tempat diskusi"):
                msg = m
                break
        if msg is None:
            msg = await channel.send(text, embed=embed)
        elif not msg.embeds or not msg.embeds[0].image or msg.embeds[0].footer.text != config.SERVER_NAME:
            msg = await msg.edit(content=text, embed=embed)
        if not msg.pinned:
            await msg.pin(reason="Minhub: pesan pembuka campaign")
        intro_done.add(channel.id)
    except discord.Forbidden:
        log.warning("Belum bisa pin di #%s: role Minhub butuh izin Pin Messages", channel.name)
    except discord.HTTPException:
        log.exception("Gagal atur pesan pembuka #%s", channel.name)


# ---------- event ----------

@client.event
async def on_ready():
    log.info("Login sebagai %s di %d server", client.user, len(client.guilds))
    try:
        await watcher.fetch()
    except Exception:
        log.exception("Gagal ambil data campaign")
    for guild in client.guilds:
        await sync_guild(guild)
    if not campaign_loop.is_running():
        campaign_loop.start()
    if not viral_loop.is_running():
        viral_loop.start()
    if not reminder_loop.is_running():
        reminder_loop.start()


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
    base = base_channel(message.channel)

    if config.CONTROL_CHANNEL.lower() in base.name.lower():
        if is_admin(message.author):
            await handle_control(message)
        return

    ref = message.reference.resolved if message.reference else None
    replied_to_bot = isinstance(ref, discord.Message) and ref.author == client.user
    mentioned = client.user in message.mentions or replied_to_bot
    slug = watcher.slug_from_topic(getattr(base, "topic", None))
    general = config.GENERAL_CHANNEL.lower() in base.name.lower()
    legacy = any(w.lower() in base.name.lower() for w in config.REPLY_CHANNELS)

    if mentioned:
        if not (slug or general or legacy):
            return
    else:
        # Mode nimbrung: cuma di #diskusi & channel campaign, cuma kalau kelihatan kayak pertanyaan.
        if not (config.AUTO_REPLY and client.intents.message_content and (slug or general)):
            return
        if isinstance(ref, discord.Message):  # lagi bales orang lain
            return
        if len(message.content) < 8 or not QUESTION_HINT.search(message.content.lower()):
            return
        if time.monotonic() - last_auto_reply.get(base.id, 0) < config.AUTO_REPLY_COOLDOWN:
            return

    await respond(message, base, slug, mentioned)


async def respond(message: discord.Message, base, slug, mentioned: bool):
    previous = last_auto_reply.get(base.id, 0)
    if not mentioned:
        last_auto_reply[base.id] = time.monotonic()  # tahan dulu biar nggak dobel

    question = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip() or "(cuma nge-tag kamu tanpa pertanyaan)"
    campaign = watcher.get(slug) if slug else None
    refs, mentions = build_refs(message.guild, campaign)
    history = await recent_history(message)

    # Jeda humanis: total 5-60 detik. Diam dulu sebentar ("baca"), lalu "typing..." sampai waktunya habis.
    total = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
    started = time.monotonic()
    answer = asyncio.create_task(brain.reply(
        question, message.author.display_name, refs, watcher.summary(),
        watcher.detail(campaign) if campaign else "", history, mentioned))
    await asyncio.sleep(min(total * 0.3, random.uniform(2, 8)))

    try:
        result = await answer
    except Exception:
        log.exception("Gagal minta jawaban ke Gemini")
        if not mentioned:
            last_auto_reply[base.id] = previous
            return
        result = {"jawab": True, "kategori": "error", "balasan": FALLBACK}

    if not result["jawab"] or not result["balasan"]:
        last_auto_reply[base.id] = previous
        log.info("[skip] %s: %s", message.author, question[:80])
        return
    log.info("[%s%s] %s: %s", result["kategori"], "" if mentioned else "/nimbrung", message.author, question[:80])

    async with message.channel.typing():
        remaining = total - (time.monotonic() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)
    await message.reply(
        fill_mentions(result["balasan"], mentions)[:2000],
        allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False, replied_user=True),
    )
    if not mentioned:
        last_auto_reply[base.id] = time.monotonic()


async def handle_control(message: discord.Message):
    """Admin ngobrol/nyuruh Minhub di channel kontrol. Pengiriman selalu lewat preview + konfirmasi ✅."""
    guild = message.guild
    channels = campaign_channels(guild)
    targets = {"diskusi": f"#{config.GENERAL_CHANNEL} (diskusi umum)",
               "pengumuman": f"#{config.CAMPAIGN_CHANNEL} (pengumuman resmi)"}
    for slug, ch in channels.items():
        c = watcher.get(slug)
        targets[slug] = f"#{ch.name} - diskusi campaign {c.get('title') if c else slug}"

    async with message.channel.typing():
        try:
            cmd = await brain.command(message.content, len(message.attachments), targets)
        except Exception:
            log.exception("Gagal proses perintah admin")
            await message.reply("Waduh, otakku error bentar 😵‍💫 coba ulangi ya.")
            return

    if cmd["aksi"] != "kirim":
        await message.reply((cmd["balasan"] or "Siap, bos 🫡")[:2000])
        return

    target = cmd["target"]
    channel = channels.get(target) or {
        "diskusi": find_channel(guild, config.GENERAL_CHANNEL),
        "pengumuman": find_channel(guild, config.CAMPAIGN_CHANNEL),
    }.get(target)
    if not channel or not cmd["pesan"]:
        await message.reply("Aku nggak nemu channel tujuannya 🤔 sebutin campaign/channel-nya lebih jelas ya.")
        return

    _, mentions = build_refs(guild, watcher.get(target))
    text = fill_mentions(cmd["pesan"], mentions)[:1900]
    n = len(message.attachments)
    preview = await message.reply(
        f"📤 Siap kirim ke {channel.mention}:\n>>> {text}"
        + (f"\n\n📎 + {n} lampiran" if n else "")
        + "\n\nReact ✅ buat kirim, ❌ buat batal (5 menit).")
    await preview.add_reaction("✅")
    await preview.add_reaction("❌")

    def check(reaction, user):
        return user.id == message.author.id and reaction.message.id == preview.id and str(reaction.emoji) in ("✅", "❌")

    try:
        reaction, _ = await client.wait_for("reaction_add", check=check, timeout=300)
    except asyncio.TimeoutError:
        await preview.reply("⌛ Kelamaan, aku batalin ya.")
        return
    if str(reaction.emoji) == "❌":
        await preview.reply("Oke, batal 👍")
        return

    files = [await a.to_file() for a in message.attachments]
    sent = await channel.send(text, files=files, allowed_mentions=discord.AllowedMentions.none())
    await preview.reply(f"✅ Terkirim: {sent.jump_url}")
    log.info("Admin %s kirim info ke #%s", message.author, channel.name)


@tasks.loop(minutes=config.CAMPAIGN_CHECK_MINUTES)
async def campaign_loop():
    try:
        new = await watcher.check_new()
    except Exception:
        log.exception("Gagal cek campaign")
        return
    for guild in client.guilds:
        await sync_guild(guild)  # bikin channel diskusi untuk campaign baru
        channels = campaign_channels(guild)
        for c in new:
            channel = find_channel(guild, config.CAMPAIGN_CHANNEL)
            if not channel:
                log.warning("Channel campaign '%s' tidak ketemu di %s", config.CAMPAIGN_CHANNEL, guild)
                continue
            text, embed = watcher.announcement(c)
            if c["slug"] in channels:
                text += f"\n💬 Diskusi: {channels[c['slug']].mention}"
            await channel.send(text, embed=embed)
            log.info("Umumkan campaign baru: %s", c["slug"])


@tasks.loop(minutes=10)
async def viral_loop():
    """Sekali sehari (mulai VIRAL_POST_HOUR WIB): share konten paling meledak ke tiap channel campaign."""
    if not viral.due():
        return
    for guild in client.guilds:
        channels = campaign_channels(guild)
        for slug, token in config.REPORTS.items():
            campaign = watcher.get(slug)
            channel = channels.get(slug)
            if not campaign or campaign.get("status", "aktif") != "aktif" or not channel:
                continue
            try:
                rec = await viral.pick(slug, token)
            except Exception:
                log.exception("Gagal baca laporan %s", slug)
                continue
            if rec:
                await channel.send(viral.message(campaign, rec),
                                   allowed_mentions=discord.AllowedMentions(everyone=True))
                log.info("Share konten meledak %s: %s views", slug, rec.get("views"))


REMINDER_FILE = os.path.join(HERE, "reminder_state.json")


@tasks.loop(hours=6)
async def reminder_loop():
    """Tiap LOGIN_REMINDER_DAYS hari, ingatkan admin login ke Wispbyte biar server gratisnya nggak dimatikan."""
    today = datetime.date.today()
    last = None
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, encoding="utf-8") as f:
            last = datetime.date.fromisoformat(json.load(f)["last"])
    if last is None:  # pertama kali jalan: mulai hitung dari hari ini
        last = today
    elif (today - last).days < config.LOGIN_REMINDER_DAYS:
        return
    else:
        for guild in client.guilds:
            channel = find_channel(guild, config.CONTROL_CHANNEL)
            role = find_role(guild, config.ADMIN_ROLE)
            if channel:
                await channel.send(
                    f"⏰ {role.mention if role else 'Admin'} pengingat rutin: login dulu ke {config.LOGIN_REMINDER_URL} "
                    f"ya (cukup buka & login). Server gratis Wispbyte dimatikan kalau 2 minggu nggak login, "
                    f"nanti aku ikut mati 😵",
                    allowed_mentions=discord.AllowedMentions(roles=True))
        last = today
    with open(REMINDER_FILE, "w", encoding="utf-8") as f:
        json.dump({"last": last.isoformat()}, f)


if __name__ == "__main__":
    client.run(os.environ["DISCORD_TOKEN"], log_handler=None)
