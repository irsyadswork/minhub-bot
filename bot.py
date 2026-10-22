"""Minhub - bot Discord Clipper Hub Circle. Jalankan: python bot.py"""
import asyncio
import datetime
import io
import json
import logging
import os
import random
import re
import socket
import sys
import time
import urllib.request
from collections import defaultdict, deque

import discord
from discord.ext import tasks
from dotenv import load_dotenv

import config
import linkpreview
import store
import texts
from ai import AIBusy, Brain
from campaigns import STATUS_EMOJI, CampaignWatcher, format_value
from tone import tidy
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
linkpreview.set_poster_lookup(lambda slug: watcher.poster(watcher.get(slug)) if watcher.get(slug) else None)

FALLBACK = "Waduh, aku lagi error bentar 😅 {admin} tolong bantu jawab ya."
BUSY = "Lagi rame banget yang nanya nih, coba tanya lagi semenit lagi ya 🙏"
RATE_LIMITED = "Pelan-pelan dulu ya, aku jawab satu-satu 😅"
STYLES = ["buka dengan pertanyaan santai", "buka langsung ke intinya", "nada kagum tapi kalem",
          "nada ngajak belajar bareng", "kalimat pendek-pendek", "sedikit bercanda", "kayak ngobrol sama temen"]
INJECTION_REPLIES = [
    "Yang itu rahasia dapur wkwk. Mending tanya soal clipping atau campaign aja.",
    "Hmm, itu nggak bisa aku kasih ya. Ada yang mau ditanya soal campaign?",
    "Skip yang itu ya 😅 kalau soal clipping, aku siap bantu.",
]
# Pesan error lama dari Minhub: jangan dibaca ulang sebagai konteks obrolan.
ERROR_HINTS = ("otakku error", "otakku lagi nge-lag", "lagi error bentar", "lagi rame banget", "gagal proses perintah",
               "gemini lagi penuh", "gagal kirim")
QUESTION_HINT = re.compile(
    r"\?|\b(gimana|bagaimana|gmn|kapan|berapa|brp|apakah|apa|bisa|boleh|cara|kenapa|knp|kok|min|mimin|admin|"
    r"tanya|nanya|brief|cair|payout|bayar|transfer|withdraw|narik|views|deadline|hashtag|upload|aturan|rules|qc|"
    r"join|minimal|maksimal|bingung)\b")
INJECTION = re.compile(
    r"system\s*prompt|prompt\s*(sistem|kamu|lu|lo|mu|awal|asli)|instruksi\s*(awal|sistem|rahasia|asli|kamu|lu|mu)|"
    r"ignore\s*(all\s*)?(previous|above|prior|the)|disregard\s*(all|previous)|"
    r"(abaikan|lupakan|hapus)\s*(semua\s*)?(instruksi|perintah|aturan)|"
    r"(api|secret)[\s_-]*key\s*(kamu|lu|lo|mu|nya|minhub|gemini|bot|discord)|"
    r"token\s*((bot|discord|gemini)\s*)?(kamu|lu|lo|mu|nya|minhub)|\.env\b|jailbreak|developer\s*mode|"
    r"(tampilkan|kasih|kirim|bocorin|sebutin|print|reveal|show|tulis\s*ulang)\s.{0,30}"
    r"(konfigurasi|config|data\s*internal|kode\s*sumber|source\s*code|instruksi|prompt)",
    re.IGNORECASE)
LEAK = re.compile(r"AIza[0-9A-Za-z_\-]{20,}|[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27,}|"
                  r"KATEGORI JAWABAN|SITUASI:|Balas HANYA dengan JSON")

last_auto_reply: dict[int, float] = {}
sync_lock = asyncio.Lock()
error_msgs: set[int] = set()
drafts: dict[int, dict] = {}
_hits: dict[int, deque] = defaultdict(deque)
_blocked: dict[int, deque] = defaultdict(deque)
_warned: dict[int, float] = {}
_last_alert: dict[str, float] = {}
started = False


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


def get_channel(guild: discord.Guild, channel_id, name: str):
    """Cari pakai ID dulu (tahan rename), nama cuma cadangan kalau ID kosong."""
    if channel_id:
        return guild.get_channel(channel_id)
    return find_channel(guild, name)


def admin_role(guild: discord.Guild):
    return guild.get_role(config.ADMIN_ROLE_ID) if config.ADMIN_ROLE_ID else find_role(guild, config.ADMIN_ROLE)


def control_channel(guild: discord.Guild):
    return get_channel(guild, config.CONTROL_CHANNEL_ID, config.CONTROL_CHANNEL)


def general_channel(guild: discord.Guild):
    return get_channel(guild, config.GENERAL_CHANNEL_ID, config.GENERAL_CHANNEL)


def is_channel(ch, channel_id, name: str) -> bool:
    return ch.id == channel_id if channel_id else name.lower() in ch.name.lower()


def home_guild():
    return client.get_guild(config.GUILD_ID) if config.GUILD_ID else (client.guilds[0] if client.guilds else None)


def base_channel(channel):
    return channel.parent if isinstance(channel, discord.Thread) and channel.parent else channel


def is_admin(member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    role = admin_role(member.guild)
    return (role in member.roles) or member.guild_permissions.manage_guild


def campaign_channels(guild: discord.Guild) -> dict:
    """slug -> channel diskusi campaign. Mapping disimpan pakai channel ID (tahan rename);
    channel baru dikenali dari topic-nya lalu ID-nya dicatat."""
    state = store.load("campaign_state.json", {})
    ids = state.setdefault("channels", {})
    found, changed = {}, False
    for slug, cid in list(ids.items()):
        ch = guild.get_channel(cid)
        if ch:
            found[slug] = ch
    for ch in guild.text_channels:
        slug = watcher.slug_from_topic(ch.topic)
        if slug and slug not in found:
            found[slug] = ch
            ids[slug] = ch.id
            changed = True
    if changed:
        store.save("campaign_state.json", state)
    return found


def build_refs(guild: discord.Guild, campaign=None) -> tuple[dict, dict]:
    """Balikin (deskripsi untuk AI, placeholder -> teks asli)."""
    refs, mentions = {}, {}
    if campaign:
        refs["{brief}"] = "halaman brief campaign ini"
        mentions["{brief}"] = watcher.link(campaign)
    for key, desc, obj in [
        ("{rules}", "channel rules", get_channel(guild, config.RULES_CHANNEL_ID, config.RULES_CHANNEL)),
        ("{admin}", "tim admin (tag mereka untuk bantu jawab)", admin_role(guild)),
    ]:
        if obj:
            refs[key] = desc
            mentions[key] = obj.mention
    return refs, mentions


def fill_mentions(text: str, mentions: dict) -> str:
    for key in ("{brief}", "{rules}", "{admin}"):
        text = text.replace(key, mentions.get(key, "admin" if key == "{admin}" else "brief di website"))
    return text.replace("@everyone", "everyone").replace("@here", "here")


def is_error_message(m: discord.Message) -> bool:
    return m.author == client.user and (m.id in error_msgs or any(h in m.content.lower() for h in ERROR_HINTS))


async def recent_history(message: discord.Message, limit: int = config.HISTORY_MESSAGES) -> str:
    lines = []
    try:
        async for m in message.channel.history(limit=limit, before=message):
            if is_error_message(m):
                continue
            name = config.BOT_NAME if m.author == client.user else m.author.display_name
            text = m.clean_content[:300] or ("[kirim lampiran]" if m.attachments else "[embed]" if m.embeds else "")
            lines.append(f"{name}: {text}")
    except discord.HTTPException:
        pass
    return "\n".join(reversed(lines))


# ---------- kirim pesan (semua teks lewat sini: tone + preview link aman) ----------

async def send(dest, text: str = "", *, embeds=None, files=None, reference=None, everyone=False,
               users=False, roles=False, raw=False) -> discord.Message:
    """raw=True: teks nggak disaring tone (dipakai untuk instruksi tombol ✅/❌ dan detail error)."""
    text = text if raw else tidy(text)
    text, extra = await linkpreview.prepare(text)
    embeds = [await linkpreview.clean_embed(e) for e in (embeds or []) + extra][:10]
    mentions = discord.AllowedMentions(everyone=everyone, users=users, roles=roles, replied_user=True)
    return await dest.send(text[:2000] or None, embeds=embeds, files=files or None, reference=reference,
                           allowed_mentions=mentions)


async def alert(text: str, key: str | None = None, cooldown: bool = True):
    """Kabari admin di #minhub-control. Alert yang sama dibatasi biar nggak spam."""
    key = key or text[:60]
    now = time.monotonic()
    if cooldown and now - _last_alert.get(key, -1e9) < config.ALERT_COOLDOWN_MINUTES * 60:
        return
    _last_alert[key] = now
    guild = home_guild()
    channel = control_channel(guild) if guild else None
    if not channel:
        log.warning("Alert nggak terkirim (channel kontrol nggak ketemu): %s", text)
        return
    try:
        await send(channel, text[:1900], raw=True)
    except discord.HTTPException:
        log.exception("Gagal kirim alert")


async def compose(task: str, facts: dict, templates: list[str], required: list[str]) -> str:
    """Tulis pesan pakai AI biar variatif; kalau gagal/kurang lengkap, pakai template."""
    fact_text = "\n".join(f"- {k}: {v}" for k, v in facts.items())
    try:
        text = await brain.write(f"{task}\nVariasi gaya kali ini: {random.choice(STYLES)}.", fact_text)
        if text and len(text) < 900 and all(r.lower() in text.lower() for r in required):
            return text
        log.info("Teks AI kurang lengkap, pakai template")
    except Exception as e:
        log.warning("Gagal nulis pesan pakai AI, pakai template: %s", e)
    return random.choice(templates).format(**facts)


# ---------- keamanan & monitoring ----------

def rate_check(user_id: int) -> bool:
    now = time.monotonic()
    q = _hits[user_id]
    while q and now - q[0] > 3600:
        q.popleft()
    per_minute = sum(1 for t in q if now - t < 60)
    if per_minute >= config.RATE_LIMIT_PER_MINUTE or len(q) >= config.RATE_LIMIT_PER_HOUR:
        return False
    q.append(now)
    return True


async def guard_guild(guild: discord.Guild) -> bool:
    """Bot cuma boleh di server sendiri. Kalau dimasukkan ke server lain, langsung keluar."""
    if not config.GUILD_ID or guild.id == config.GUILD_ID:
        return True
    log.warning("Keluar dari server asing: %s (%s)", guild.name, guild.id)
    store.activity(kind="leave_guild", guild=guild.name, guild_id=guild.id)
    try:
        await guild.leave()
    except discord.HTTPException:
        log.exception("Gagal keluar dari %s", guild.name)
    await alert(f"Ada yang masukin aku ke server lain: **{guild.name}** (ID {guild.id}). Udah aku tinggal keluar.",
                cooldown=False)
    return False


def host_label() -> str:
    return "Wispbyte" if os.path.isdir("/home/container") else f"PC/host lain ({socket.gethostname()})"


def git_version() -> str:
    try:
        with open(os.path.join(HERE, ".git", "HEAD")) as f:
            head = f.read().strip()
        if head.startswith("ref:"):
            ref = head.split(" ", 1)[1]
            path = os.path.join(HERE, ".git", *ref.split("/"))
            if os.path.exists(path):
                with open(path) as f:
                    return f.read().strip()[:7]
            with open(os.path.join(HERE, ".git", "packed-refs")) as f:
                for line in f:
                    if line.strip().endswith(ref):
                        return line[:7]
        return head[:7]
    except OSError:
        return "?"


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
            if not general_channel(guild):
                ch = await guild.create_text_channel(
                    config.GENERAL_CHANNEL, overwrites=public_overwrites(guild),
                    topic=f"Ngobrol bebas seputar clipping. {config.BOT_NAME} standby buat jawab pertanyaan.",
                    reason="Minhub: channel diskusi umum")
                log.info("Bikin channel #%s", ch.name)

            if not control_channel(guild):
                admin = admin_role(guild)
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
                await send(ch, "Halo admin! Di sini kalian bisa nyuruh aku, contoh: kirim screenshot + "
                               "*\"di #pengumuman share ini, bilang ada angle baru\"*. Aku kasih preview dulu sebelum dikirim.")
                log.info("Bikin channel #%s", ch.name)

            existing = campaign_channels(guild)
            category = None
            for c in watcher.active():
                if c["slug"] in existing:
                    continue
                if category is None:
                    category = (guild.get_channel(config.CAMPAIGN_CATEGORY_ID) if config.CAMPAIGN_CATEGORY_ID else None) \
                        or discord.utils.find(lambda k: k.name.lower() == config.CAMPAIGN_CATEGORY.lower(),
                                              guild.categories) \
                        or await guild.create_category(config.CAMPAIGN_CATEGORY, reason="Minhub")
                ch = await guild.create_text_channel(
                    watcher.channel_name(c), category=category, topic=watcher.channel_topic(c),
                    overwrites=public_overwrites(guild), reason=f"Minhub: diskusi campaign {c['slug']}")
                existing[c["slug"]] = ch
                state = store.load("campaign_state.json", {})
                state.setdefault("channels", {})[c["slug"]] = ch.id
                store.save("campaign_state.json", state)
                log.info("Bikin channel #%s", ch.name)
                await ensure_intro(ch, c, tag_everyone=True)  # campaign baru: kabari semua member
        except discord.Forbidden:
            log.warning("Minhub belum punya izin Manage Channels / Manage Roles, channel nggak bisa dibuat otomatis")
            await alert("Aku nggak bisa bikin channel otomatis: izin **Manage Channels / Manage Permissions** di "
                        "kategori Diskusi Campaign belum ada.", key="perm:create")
            return

        for slug, ch in existing.items():
            c = watcher.get(slug)
            if c and ch.id not in intro_done:
                await ensure_intro(ch, c)


intro_done: set[int] = set()


async def ensure_intro(channel: discord.TextChannel, c: dict, tag_everyone: bool = False):
    """Pastikan pesan pembuka campaign (versi dengan banner) ada dan di-pin."""
    text, embed = watcher.intro(c)
    if tag_everyone:
        text = "@everyone " + text
    msg = None
    try:
        async for m in channel.history(limit=50, oldest_first=True):
            if (m.author == client.user and "Ini tempat diskusi" in m.content
                    and m.embeds and m.embeds[0].footer.text == config.SERVER_NAME):
                msg = m
                break
        if msg is None:
            msg = await send(channel, text, embeds=[embed], everyone=tag_everyone)
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
    global started
    log.info("Login sebagai %s di %d server", client.user, len(client.guilds))
    for guild in list(client.guilds):
        await guard_guild(guild)
    if started:  # on_ready bisa kepanggil lagi setelah reconnect
        return
    started = True
    await announce_startup()
    try:
        await watcher.fetch()
    except Exception:
        log.exception("Gagal ambil data campaign")
    for guild in client.guilds:
        await sync_guild(guild)
    for loop in (campaign_loop, viral_loop, reminder_loop, status_loop, daily_loop, heartbeat_loop):
        if not loop.is_running():
            loop.start()


async def announce_startup():
    """Alert ke admin tiap bot nyala. Ketahuan juga kalau sebelumnya mati mendadak atau ada bot dobel."""
    state = store.load("bot_state.json", {})
    beat, clean = state.get("heartbeat"), state.get("clean_stop")
    if not beat:
        why = "Ini start pertama dengan sistem alert."
    elif clean and clean >= beat:
        why = f"Sebelumnya dimatikan normal ({clean[:16].replace('T', ' ')} WIB)."
    else:
        why = (f"Sebelumnya mati mendadak/crash, terakhir kelihatan hidup {beat[:16].replace('T', ' ')} WIB. "
               f"Cek log Wispbyte kalau perlu.")
    state["clean_stop"] = None
    store.save("bot_state.json", state)
    store.activity(kind="startup", host=host_label(), version=git_version())
    await alert(f"Minhub nyala lagi di **{host_label()}** (versi `{git_version()}`). {why}\n"
                f"Kalau host-nya bukan Wispbyte, berarti ada Minhub dobel yang jalan, matikan salah satunya ya.",
                cooldown=False)


@client.event
async def on_guild_join(guild: discord.Guild):
    await guard_guild(guild)


@client.event
async def on_error(event, *args, **kwargs):
    exc = sys.exc_info()[1]
    log.exception("Error di event %s", event)
    await alert(f"Ada error di `{event}`: `{type(exc).__name__}: {str(exc)[:300]}`", key=f"err:{event}")


@client.event
async def on_member_join(member: discord.Member):
    if member.guild.id != config.GUILD_ID:
        return
    store.event("member_join", user=member.name, user_id=member.id)
    channel = get_channel(member.guild, config.WELCOME_CHANNEL_ID, config.WELCOME_CHANNEL)
    if not channel:
        log.warning("Channel welcome '%s' tidak ketemu", config.WELCOME_CHANNEL)
        return
    try:
        avatar = await member.display_avatar.replace(format="png", size=256).read()
        card = await asyncio.to_thread(make_welcome_card, avatar, member.name)
        text = random.choice(texts.WELCOME).format(mention=member.mention, server=config.SERVER_NAME)
        await send(channel, text, files=[discord.File(card, "welcome.png")], users=True)
        store.event("welcome_sent", user=member.name, user_id=member.id)
    except Exception:
        log.exception("Gagal kirim welcome untuk %s", member)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild or message.guild.id != config.GUILD_ID:
        return
    base = base_channel(message.channel)

    if is_channel(base, config.CONTROL_CHANNEL_ID, config.CONTROL_CHANNEL):
        if is_admin(message.author):
            await handle_control(message)
        else:
            store.activity(kind="control_non_admin", user=str(message.author), user_id=message.author.id,
                           text=message.content[:200])
            await alert(f"{message.author.mention} (bukan admin) nulis di channel kontrol: "
                        f"\"{message.content[:200]}\". Cek izin channel ini ya.", key=f"ctl:{message.author.id}")
        return

    ref = message.reference.resolved if message.reference else None
    replied_to_bot = isinstance(ref, discord.Message) and ref.author == client.user
    mentioned = client.user in message.mentions or replied_to_bot
    slug = watcher.slug_from_topic(getattr(base, "topic", None))
    general = is_channel(base, config.GENERAL_CHANNEL_ID, config.GENERAL_CHANNEL)
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

    if not is_admin(message.author) and not await passes_security(message, base, mentioned):
        return
    await respond(message, base, slug, mentioned)


async def passes_security(message: discord.Message, base, mentioned: bool) -> bool:
    """Deteksi prompt injection & rate limit per member. Yang mencurigakan dilaporkan ke channel kontrol."""
    author = message.author
    if INJECTION.search(message.content):
        store.activity(kind="prompt_injection", user=str(author), user_id=author.id, channel=base.name,
                       text=message.content[:300])
        log.warning("[injection] %s: %s", author, message.content[:120])
        await alert(f"Aktivitas mencurigakan: {author.mention} kayaknya nyoba ngorek data internal/prompt di "
                    f"{base.mention}:\n> {message.content[:300]}", key=f"inj:{author.id}")
        if mentioned:
            await send(message.channel, random.choice(INJECTION_REPLIES), reference=message)
        return False

    if rate_check(author.id):
        return True
    now = time.monotonic()
    blocked = _blocked[author.id]
    blocked.append(now)
    while blocked and now - blocked[0] > 600:
        blocked.popleft()
    store.activity(kind="rate_limited", user=str(author), user_id=author.id, channel=base.name,
                   text=message.content[:200])
    if mentioned and now - _warned.get(author.id, -1e9) > 300:
        _warned[author.id] = now
        await send(message.channel, RATE_LIMITED, reference=message)
    if len(blocked) >= 5:
        await alert(f"Aktivitas mencurigakan: {author.mention} nge-spam pertanyaan ke aku di {base.mention} "
                    f"({len(blocked)}x kena rate limit dalam 10 menit).", key=f"spam:{author.id}")
    return False


async def respond(message: discord.Message, base, slug, mentioned: bool):
    previous = last_auto_reply.get(base.id, 0)
    if not mentioned:
        last_auto_reply[base.id] = time.monotonic()  # tahan dulu biar nggak dobel

    question = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip() or "(cuma nge-tag kamu tanpa pertanyaan)"
    campaign = watcher.get(slug) if slug else None
    refs, mentions = build_refs(message.guild, campaign)
    history = await recent_history(message)
    kind = "question" if mentioned else "nimbrung"

    # Jeda humanis: total 5-60 detik. Diam dulu sebentar ("baca"), lalu "typing..." sampai waktunya habis.
    total = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
    started_at = time.monotonic()
    answer = asyncio.create_task(brain.reply(
        question, message.author.display_name, refs, watcher.summary(),
        watcher.detail(campaign) if campaign else "", history, mentioned))
    await asyncio.sleep(min(total * 0.3, random.uniform(2, 8)))

    try:
        result = await answer
    except Exception as e:
        busy = isinstance(e, AIBusy)
        log.warning("Gagal minta jawaban ke Gemini: %s", e)
        store.activity(kind=kind, user=str(message.author), user_id=message.author.id, channel=base.name,
                       text=question[:200], result="busy" if busy else "error", reason=str(e)[:300])
        await alert(f"Gagal jawab {message.author.mention} di {base.mention} "
                    f"({'Gemini lagi penuh' if busy else 'error'}): `{str(e)[:400]}`",
                    key="ai:busy" if busy else "ai:error")
        if not mentioned:
            last_auto_reply[base.id] = previous
            return
        result = {"jawab": True, "kategori": "busy" if busy else "error", "balasan": BUSY if busy else FALLBACK}

    if not result["jawab"] or not result["balasan"]:
        last_auto_reply[base.id] = previous
        log.info("[skip] %s: %s", message.author, question[:80])
        return
    if LEAK.search(result["balasan"]):
        await alert(f"Jawaban AI buat {message.author.mention} keliatan bocorin data internal, aku blokir.",
                    key=f"leak:{message.author.id}")
        result["balasan"] = random.choice(INJECTION_REPLIES)
    log.info("[%s%s] %s: %s", result["kategori"], "" if mentioned else "/nimbrung", message.author, question[:80])
    store.activity(kind=kind, user=str(message.author), user_id=message.author.id, channel=base.name,
                   text=question[:200], result=result["kategori"])

    async with message.channel.typing():
        remaining = total - (time.monotonic() - started_at)
        if remaining > 0:
            await asyncio.sleep(remaining)
    sent = await send(message.channel, fill_mentions(result["balasan"], mentions), reference=message,
                      users=True, roles=True)
    if result["kategori"] in ("busy", "error"):
        error_msgs.add(sent.id)
    if not mentioned:
        last_auto_reply[base.id] = time.monotonic()


# ---------- perintah admin di #minhub-control ----------

async def control_reply(message: discord.Message, text: str, error: bool = False):
    sent = await send(message.channel, text, reference=message, raw=error)
    if error:
        error_msgs.add(sent.id)
    return sent


async def handle_control(message: discord.Message):
    """Admin ngobrol/nyuruh Minhub di channel kontrol. Pengiriman selalu lewat preview + konfirmasi ✅.
    Channel tujuan diambil dari mention channel (#pengumuman); kalau nggak disebut, Minhub nanya dulu."""
    author = message.author
    targets = [c for c in message.channel_mentions
               if c.id != message.channel.id and isinstance(c, (discord.TextChannel, discord.Thread))]
    draft = drafts.get(author.id)
    if draft and time.monotonic() - draft["t"] > 1800:
        draft = None
        drafts.pop(author.id, None)
    store.activity(kind="admin_command", user=str(author), user_id=author.id, text=message.content[:300],
                   targets=[c.name for c in targets])

    # Admin nge-reply pesan Minhub: isi pesan itu ikut jadi konteks (biar "ini ke #channel" nyambung)
    ref = message.reference.resolved if message.reference else None
    replied, reply_viral = "", None
    if isinstance(ref, discord.Message) and ref.author == client.user:
        replied = ref.clean_content[:600] + (f" [kartu: {ref.embeds[0].title}]" if ref.embeds else "")
        reply_viral = viral_ask_for(ref.id)
        if reply_viral:
            replied += f" (ini usulan konten viral id {reply_viral})"
        elif draft and ref.id in draft.get("preview_ids", ()):
            replied += " (ini preview draf terakhir; balasan admin = revisi atau keputusan untuk draf itu)"

    try:
        async with message.channel.typing():
            cmd = await brain.command(
                message.clean_content, len(message.attachments),
                ", ".join(f"#{c.name}" for c in targets), await recent_history(message, 8),
                (draft["text"] + (f" (tujuan: #{draft['channel']})" if draft.get("channel") else "")) if draft else "",
                store.recap(), pending_deadlines_text(), replied, pending_virals_text())
    except AIBusy as e:
        log.warning("Perintah admin: Gemini penuh: %s", e)
        await control_reply(message, f"Gemini lagi penuh (503/429/timeout), udah dicoba ulang tapi masih gagal. "
                                     f"Coba lagi semenit lagi ya.\nDetail: `{str(e)[:500]}`", error=True)
        return
    except Exception as e:
        log.exception("Gagal proses perintah admin")
        await control_reply(message, f"Gagal proses perintah: `{type(e).__name__}: {str(e)[:500]}`", error=True)
        return

    log.info("[admin/%s] %s: %s", cmd["aksi"], author, message.content[:80])
    if cmd["aksi"] == "viral":
        decided = [d for d in cmd["keputusan"] if d["keputusan"] in ("kirim", "ganti", "skip", "revisi")]
        if not decided:
            await control_reply(message, cmd["balasan"] or "Mau diapain usulannya? Acc, ganti, atau skip?")
        for d in decided:
            ask_id = d["id"] if d["id"] in pending_virals() else reply_viral
            try:
                await decide_viral(ask_id, d["keputusan"], author, d["pesan_baru"], reference=message)
            except discord.HTTPException as e:
                log.exception("Gagal proses keputusan konten viral")
                await control_reply(message, f"Gagal kirim: `{type(e).__name__} {e.status}: {e.text[:300]}`",
                                    error=True)
        return
    decisions = [d for d in cmd["keputusan"] if d["keputusan"] in ("closed", "extend")]
    if cmd["aksi"] == "deadline" and decisions:
        for d in decisions:
            try:
                await decide_deadline(message, d["slug"], d["keputusan"], d["tanggal_baru"])
            except discord.HTTPException as e:
                log.exception("Gagal proses keputusan deadline")
                await control_reply(message, f"Gagal umumin: `{type(e).__name__} {e.status}: {e.text[:300]}`",
                                    error=True)
        return
    if cmd["aksi"] not in ("kirim", "preview"):
        await control_reply(message, cmd["balasan"] or "Siap.")
        return

    text = cmd["pesan"] or (draft["text"] if draft else "")
    source = message if message.attachments else (draft.get("source") if draft else None)
    if not text and not source:
        await control_reply(message, "Pesan apa yang mau dikirim? Tulis aja isinya ya.")
        return
    target = targets[0] if targets else (message.guild.get_channel(draft["channel_id"])
                                         if draft and draft.get("channel_id") else None)
    drafts[author.id] = {"text": text, "source": source, "channel_id": target.id if target else None,
                         "channel": target.name if target else None, "t": time.monotonic(),
                         "version": (draft or {}).get("version", 0) + 1, "preview_ids": []}

    if cmd["aksi"] == "kirim" and not target:
        await control_reply(message, "Mau dikirim ke channel mana? Sebut channel-nya ya, misal #pengumuman.")
        return
    try:
        await preview_and_send(message, text, source, target)
    except discord.HTTPException as e:
        log.exception("Gagal kirim/preview perintah admin")
        await control_reply(message, f"Gagal kirim: `{type(e).__name__} {e.status}: {e.text[:300]}`", error=True)


async def preview_and_send(message: discord.Message, text: str, source, target):
    guild = message.guild
    _, mentions = build_refs(guild)
    text = fill_mentions(tidy(text), mentions)[:1900]
    text, embeds = await linkpreview.prepare(text)
    embeds = [await linkpreview.clean_embed(e) for e in embeds]

    async def files():
        return [await a.to_file() for a in source.attachments] if source else []

    draft = drafts.get(message.author.id) or {}
    version = draft.get("version")
    header = await control_reply(message, f"Preview pesan{' ke ' + target.mention if target else ''} (persis kayak gini):")
    shown = await message.channel.send(text or None, embeds=embeds, files=await files(),
                                       allowed_mentions=discord.AllowedMentions.none())
    draft.setdefault("preview_ids", []).extend([header.id, shown.id])
    if not target:
        await send(message.channel, "Kalau udah oke, sebut channel tujuannya ya, misal *kirim ke #pengumuman*.")
        return
    perms = target.permissions_for(guild.me)
    if not (perms.view_channel and perms.send_messages):
        await control_reply(message, f"Aku nggak punya izin kirim pesan di {target.mention}. "
                                     f"Tambahin izin View Channel + Send Messages buat role Minhub di sana.", error=True)
        return

    confirm = await message.channel.send("React ✅ buat kirim, ❌ buat batal (5 menit). Mau revisi? Bales pesan ini "
                                         "atau preview di atas pakai koreksinya.")
    draft.setdefault("preview_ids", []).append(confirm.id)
    await confirm.add_reaction("✅")
    await confirm.add_reaction("❌")

    def check(reaction, user):
        return user.id == message.author.id and reaction.message.id == confirm.id and str(reaction.emoji) in ("✅", "❌")

    try:
        reaction, _ = await client.wait_for("reaction_add", check=check, timeout=300)
    except asyncio.TimeoutError:
        await send(confirm.channel, "Kelamaan, aku batalin ya. Draf masih aku inget 30 menit.", reference=confirm)
        return
    if str(reaction.emoji) == "❌":
        await send(confirm.channel, "Oke, batal 👍", reference=confirm)
        return
    current = drafts.get(message.author.id)
    if current and current.get("version") != version:
        await send(confirm.channel, "Ini preview lama, udah ada revisinya. Pakai preview yang terbaru ya.",
                   reference=confirm)
        return

    sent = await target.send(text or None, embeds=embeds, files=await files(),
                             allowed_mentions=discord.AllowedMentions.none())
    drafts.pop(message.author.id, None)
    await send(confirm.channel, f"Terkirim: {sent.jump_url}", reference=confirm)
    store.activity(kind="admin_send", user=str(message.author), user_id=message.author.id, channel=target.name,
                   text=text[:300])
    log.info("Admin %s kirim info ke #%s", message.author, target.name)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Admin react ✅ di preview pengingat harian -> pengingat aktif."""
    if payload.user_id == client.user.id or not payload.guild_id:
        return
    guild = client.get_guild(payload.guild_id)
    member = payload.member or (guild.get_member(payload.user_id) if guild else None)
    if str(payload.message_id) in pending_virals():
        decision = VIRAL_REACTIONS.get(str(payload.emoji))
        if decision and is_admin(member):
            await decide_viral(str(payload.message_id), decision, member)
        return
    if str(payload.emoji) != "✅":
        return
    state = store.load("bot_state.json", {})
    daily = state.get("daily") or {}
    if daily.get("enabled") or payload.message_id != daily.get("preview_id"):
        return
    if not is_admin(member):
        return
    now = store.now_wib()
    daily["enabled"] = True
    if now.hour >= config.DAILY_REMINDER_HOUR:
        daily["last"] = now.date().isoformat()  # jangan langsung kirim kalau sudah lewat jamnya
    state["daily"] = daily
    store.save("bot_state.json", state)
    store.activity(kind="daily_reminder_enabled", user=str(member), user_id=member.id)
    channel = general_channel(guild)
    note = ""
    if channel and not channel.permissions_for(guild.me).mention_everyone:
        note = " Tapi role Minhub belum punya izin **Mention Everyone** di channel itu, tolong ditambahin ya."
    await alert(f"Sip, pengingat harian aktif. Aku kirim ke {channel.mention if channel else '#diskusi-general'} "
                f"tiap jam {config.DAILY_REMINDER_HOUR}.00 WIB.{note}", cooldown=False)


# ---------- tugas berkala ----------

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
            channel = get_channel(guild, config.CAMPAIGN_CHANNEL_ID, config.CAMPAIGN_CHANNEL)
            if not channel:
                log.warning("Channel campaign '%s' tidak ketemu di %s", config.CAMPAIGN_CHANNEL, guild)
                continue
            try:
                await announce_campaign(channel, c, channels.get(c["slug"]))
            except Exception as e:
                log.exception("Gagal umumkan campaign %s", c["slug"])
                await alert(f"Gagal umumin campaign baru **{c.get('title')}**: `{e}`")


async def announce_campaign(channel, c: dict, discussion):
    facts = watcher.announce_facts(c)
    facts["channel"] = discussion.mention if discussion else "channel diskusinya"
    text = await compose(
        "Umumkan campaign clipping baru ke semua member. 1-2 kalimat, wording segar (jangan template promosi). "
        "Wajib sebut nama campaign, brand, rate, dan deadline, lalu arahkan diskusi ke {channel} "
        "(tulis {channel} persis begitu). Jangan tulis link (link sudah ada di kartu di bawahnya).",
        {**facts, "channel": "{channel}"}, texts.ANNOUNCE, [facts["title"], "{channel}"])
    text = text.replace("{channel}", facts["channel"])
    await send(channel, "@everyone " + text, embeds=[watcher.announcement(c)], everyone=True)
    store.event("campaign_announced", slug=c["slug"])
    log.info("Umumkan campaign baru: %s", c["slug"])


VIRAL_PENDING = "viral_pending.json"   # id pesan usulan di #minhub-control -> usulan konten viral yang nunggu acc
VIRAL_CACHE = os.path.join(HERE, ".viral_cache")
VIRAL_REACTIONS = {"✅": "kirim", "🔁": "ganti", "❌": "skip"}


@tasks.loop(minutes=10)
async def viral_loop():
    """Sekali sehari (mulai VIRAL_POST_HOUR WIB): usulkan konten paling meledak tiap campaign ke admin dulu.
    Baru dikirim ke channel campaign setelah admin acc. Admin bisa minta ganti (link curang/mati) atau skip."""
    if not viral.due():
        return
    guild = home_guild()
    if not guild:
        return
    channels = campaign_channels(guild)
    waiting = {p["slug"] for p in store.load(VIRAL_PENDING, {}).values()}
    for slug, token in config.REPORTS.items():
        campaign = watcher.get(slug)
        channel = channels.get(slug)
        if (not campaign or campaign.get("status", "aktif") != "aktif" or not channel
                or slug in waiting or viral.done_today(slug)):
            continue
        try:
            await propose_viral(guild, campaign, channel)
        except Exception as e:
            log.exception("Gagal usulin konten viral %s", slug)
            await alert(f"Gagal nyiapin konten viral **{campaign.get('title')}**: `{e}`", key=f"viral:{slug}")


def viral_embed(facts: dict, caption: str | None, has_image: bool) -> discord.Embed:
    embed = discord.Embed(title=f"Klip {facts['user']} di {facts['platform']}", url=facts["link"],
                          description=(caption or "")[:200] or None, color=0x488CFF)
    embed.add_field(name="👤 Kreator", value=facts["user"], inline=True)
    embed.add_field(name="📱 Platform", value=facts["platform"], inline=True)
    embed.add_field(name="👀 Views", value=facts["views"], inline=True)
    embed.add_field(name="🏷️ Campaign", value=facts["title"], inline=False)
    embed.add_field(name="🔗 Link", value=facts["link"], inline=False)
    if has_image:
        embed.set_thumbnail(url="attachment://preview.jpg")
    embed.set_footer(text=config.SERVER_NAME)
    return embed


def viral_files(image: bytes | None) -> list:
    return [discord.File(io.BytesIO(image), "preview.jpg")] if image else []


def viral_image(ask_id) -> bytes | None:
    try:
        with open(os.path.join(VIRAL_CACHE, f"{ask_id}.jpg"), "rb") as f:
            return f.read()
    except OSError:
        return None


async def propose_viral(guild: discord.Guild, campaign: dict, channel):
    """Cari konten views terbesar yang belum pernah di-share/diganti, lalu usulkan ke admin."""
    slug = campaign["slug"]
    ctl = control_channel(guild)
    candidates = await viral.candidates(slug, config.REPORTS[slug])
    if not candidates:
        viral.mark_skipped(slug)
        return False
    rec = candidates[0]
    facts = viral.facts(campaign, rec)
    preview = await linkpreview.content_preview(facts["link"])
    text = await compose(
        "Kabari member di channel campaign ini bahwa ada klip yang lagi viral, biar mereka belajar dari klip itu. "
        "1-2 kalimat, wording variatif dan nggak template. Wajib sebut username kreator persis, nama campaign, "
        "platform, dan jumlah views. Jangan tulis link (link ada di kartu preview).",
        {k: v for k, v in facts.items() if k != "link"}, texts.VIRAL, [facts["user"], facts["views"]])
    await show_viral_proposal(ctl, campaign, channel, rec, text, (preview or {}).get("caption"),
                              (preview or {}).get("image"), len(candidates) - 1)
    return True


async def show_viral_proposal(ctl, campaign: dict, channel, rec: dict, text: str, caption, image, others: int):
    facts = viral.facts(campaign, rec)
    role = admin_role(ctl.guild)
    await send(ctl, f"{role.mention + ' ' if role else ''}Usulan konten top views buat {channel.mention} "
                    f"(persis kayak gini):", roles=True)
    preview_msg = await ctl.send("@everyone " + tidy(text), embeds=[viral_embed(facts, caption, bool(image))],
                                 files=viral_files(image), allowed_mentions=discord.AllowedMentions.none())
    note = "" if image else "\nPreview gambarnya gagal diambil, jadi kalau di-acc aku kirim tanpa gambar."
    ask = await ctl.send(
        f"Acc dikirim? Cek dulu link-nya masih ada dan views-nya wajar ya.{note}\n"
        f"React ✅ kirim, 🔁 ganti konten lain ({others} kandidat lagi), ❌ skip hari ini. Atau bales pesan ini "
        f"pakai chat biasa, misal *acc*, *ganti*, *skip*, atau *revisi kalimatnya jadi ...*.")
    for emoji in VIRAL_REACTIONS:
        await ask.add_reaction(emoji)
    if image:
        os.makedirs(VIRAL_CACHE, exist_ok=True)
        with open(os.path.join(VIRAL_CACHE, f"{ask.id}.jpg"), "wb") as f:
            f.write(image)
    pending = store.load(VIRAL_PENDING, {})
    pending[str(ask.id)] = {"slug": campaign["slug"], "channel_id": channel.id, "rec": rec, "text": text,
                            "caption": caption, "preview_id": preview_msg.id}
    store.save(VIRAL_PENDING, pending)
    store.event("viral_proposed", slug=campaign["slug"], link=rec["link"])
    log.info("Usulan konten viral %s: %s", campaign["slug"], rec["link"])


def pending_virals() -> dict:
    return store.load(VIRAL_PENDING, {})


def pending_virals_text() -> str:
    lines = []
    for ask_id, p in pending_virals().items():
        c = watcher.get(p["slug"]) or {"title": p["slug"]}
        facts = viral.facts(c, p["rec"])
        lines.append(f"- id: {ask_id} | {facts['title']} | {facts['user']} di {facts['platform']}, "
                     f"{facts['views']} views | {facts['link']}")
    return "\n".join(lines)


def viral_ask_for(message_id: int) -> str | None:
    """Id usulan dari pesan yang dibalas admin (pesan pertanyaan acc atau pesan preview-nya)."""
    for ask_id, p in pending_virals().items():
        if message_id in (int(ask_id), p.get("preview_id")):
            return ask_id
    return None


async def decide_viral(ask_id: str, decision: str, member, new_text: str = "", reference=None):
    """Keputusan admin untuk usulan konten viral: kirim / ganti / skip / revisi."""
    pending = pending_virals()
    p = pending.pop(str(ask_id), None)
    guild = home_guild()
    ctl = control_channel(guild)
    if not p:
        await send(ctl, "Usulan itu udah nggak aktif (mungkin udah diputusin).", reference=reference)
        return
    store.save(VIRAL_PENDING, pending)
    image = viral_image(ask_id)
    try:
        os.remove(os.path.join(VIRAL_CACHE, f"{ask_id}.jpg"))
    except OSError:
        pass
    slug, rec = p["slug"], p["rec"]
    campaign = watcher.get(slug) or {"slug": slug, "title": slug}
    channel = guild.get_channel(p["channel_id"])
    store.activity(kind="viral_decision", user=str(member), user_id=member.id, slug=slug, link=rec["link"],
                   decision=decision)

    if decision == "kirim":
        if not channel:
            await send(ctl, f"Channel campaign **{campaign.get('title')}** nggak ketemu, batal kirim.", reference=reference)
            return
        facts = viral.facts(campaign, rec)
        msg = await send(channel, "@everyone " + p["text"], embeds=[viral_embed(facts, p.get("caption"), bool(image))],
                         files=viral_files(image), everyone=True)
        viral.mark_posted(slug, rec)
        store.event("viral_alert_sent", slug=slug, link=rec["link"])
        await send(ctl, f"Oke, udah aku kirim: {msg.jump_url}", reference=reference)
    elif decision == "ganti":
        viral.mark_rejected(slug, rec["link"])
        await send(ctl, f"Siap, link {rec['link']} nggak bakal aku usulin lagi. Aku cariin yang lain ya.",
                   reference=reference)
        if channel and not await propose_viral(guild, campaign, channel):
            await send(ctl, f"Nggak ada kandidat lain buat **{campaign.get('title')}** yang views-nya memenuhi syarat, "
                            f"jadi hari ini di-skip dulu.")
    elif decision == "revisi" and new_text and channel:
        others = len(await viral.candidates(slug, config.REPORTS[slug])) - 1
        await show_viral_proposal(ctl, campaign, channel, rec, new_text, p.get("caption"), image, max(others, 0))
    else:
        viral.mark_skipped(slug)
        await send(ctl, f"Oke, konten viral **{campaign.get('title')}** hari ini di-skip.", reference=reference)


@tasks.loop(minutes=config.STATUS_CHECK_MINUTES)
async def status_loop():
    """Status sisa budget di nama channel campaign (🟢/🟡/🔴), update data campaign, dan pengingat deadline."""
    try:
        await watcher.fetch()
    except Exception as e:
        log.warning("Cek status campaign gagal: %s", e)
        return
    guild = home_guild()
    if not guild:
        return
    channels = campaign_channels(guild)  # sebelum load state: fungsi ini bisa nyimpen mapping channel baru
    state = store.load("campaign_state.json", {})
    first_run = "status" not in state
    status, snap, sent = state.setdefault("status", {}), state.setdefault("snap", {}), state.setdefault("deadline_sent", {})
    changes, summary = [], []

    for slug, ch in channels.items():
        c = watcher.get(slug)
        pct = watcher.remaining_pct(c) if c else None
        st = watcher.budget_status(pct)
        if not st:
            continue
        summary.append(f"{STATUS_EMOJI[st]} {c.get('title')}: sisa {watcher.pct_text(pct)}")
        want = watcher.channel_name(c, st)
        if ch.name != want:
            try:
                await ch.edit(name=want, reason=f"Minhub: sisa budget {watcher.pct_text(pct)}")
                await asyncio.sleep(2)
            except discord.Forbidden:
                await alert("Aku nggak bisa ganti nama channel campaign: izin **Manage Channels** di kategori "
                            "Diskusi Campaign belum ada.", key="perm:rename")
            except discord.HTTPException as e:
                log.warning("Gagal rename #%s: %s", ch.name, e)
        prev = status.get(slug)
        if prev != st:
            status[slug] = st
            if prev:
                changes.append(f"{STATUS_EMOJI[prev]} → {STATUS_EMOJI[st]} **{c.get('title')}** "
                               f"(sisa {watcher.pct_text(pct)}) {ch.mention}")
                if st == "red":
                    await send(ch, texts.BUDGET_RED.format(title=c.get("title")))
                    store.event("status_alert_sent", slug=slug, status=st)

    if first_run and summary:
        await alert("Status budget di nama channel campaign udah aktif:\n" + "\n".join(summary), cooldown=False)
    elif changes:
        await alert("Status budget campaign berubah:\n" + "\n".join(changes), cooldown=False)
        store.event("status_alert_sent", count=len(changes))
    store.save("campaign_state.json", state)

    # Perubahan data campaign -> kabari di channel campaign itu (bukan di #pengumuman)
    for c in watcher.campaigns:
        new = watcher.snapshot(c)
        old = snap.get(c["slug"])
        snap[c["slug"]] = new
        ch = channels.get(c["slug"])
        if old is None or not ch:
            continue
        lines = watcher.diff(old, new)
        if lines:
            opener = random.choice(texts.UPDATE_OPENER).format(title=c.get("title"))
            await send(ch, opener + "\n" + "\n".join(f"- {l}" for l in lines) + f"\nBrief lengkap: {watcher.link(c)}")
            store.event("campaign_update_sent", slug=c["slug"], changes=len(lines))
            log.info("Update campaign %s: %d perubahan", c["slug"], len(lines))

    # Pengingat deadline H-1 dan hari H
    now = store.now_wib()
    if now.hour >= config.DEADLINE_REMINDER_HOUR:
        for c in watcher.active():
            ch = channels.get(c["slug"])
            try:
                days = (datetime.date.fromisoformat(c.get("deadline")) - now.date()).days
            except (TypeError, ValueError):
                continue
            key = {1: "H-1", 0: "H-tanya"}.get(days)
            done = sent.setdefault(c["slug"], [])
            if not ch or not key or f"{key}:{c.get('deadline')}" in done:
                continue
            facts = watcher.announce_facts(c)
            done.append(f"{key}:{c.get('deadline')}")
            store.save("campaign_state.json", state)  # catat dulu biar nggak kekirim dobel kalau ada error
            if key == "H-1":
                msg = await send(ch, random.choice(texts.DEADLINE_H1).format(**facts))
                store.event("deadline_reminder_sent", slug=c["slug"], reminder=key)
                log.info("Pengingat deadline H-1 %s: %s", c["slug"], msg.jump_url)
            else:
                await ask_deadline(guild, c, ch)

    store.save("campaign_state.json", state)


async def ask_deadline(guild: discord.Guild, c: dict, channel):
    """Hari H: jangan langsung umumin. Tanya atasan dulu di channel kontrol pakai chat biasa: extend atau closed?
    Jawabannya (chat biasa juga) dipahami di handle_control."""
    ctl = control_channel(guild)
    if not ctl:
        return
    roles = [r for r in (admin_role(guild), guild.get_role(config.MENTOR_ROLE_ID)) if r]
    facts = watcher.announce_facts(c)
    msg = await send(ctl, texts.DEADLINE_ASK.format(roles=" ".join(r.mention for r in roles) or "Admin",
                                                    channel=channel.mention, **facts), roles=True)
    asks = store.load("deadline_state.json", {})
    asks[c["slug"]] = {"channel_id": channel.id, "deadline": c.get("deadline"), "message_id": msg.id}
    store.save("deadline_state.json", asks)
    store.event("deadline_ask_sent", slug=c["slug"])
    log.info("Tanya admin soal deadline %s: %s", c["slug"], msg.jump_url)


def pending_deadlines() -> dict:
    """Pertanyaan deadline hari H yang belum dijawab atasan: slug -> info. Disimpan terpisah dari campaign_state
    biar nggak ketimpa status_loop."""
    return store.load("deadline_state.json", {})


def pending_deadlines_text() -> str:
    lines = []
    for slug, ask in pending_deadlines().items():
        c = watcher.get(slug) or {}
        lines.append(f"- slug: {slug} | {c.get('title', slug)} | deadline {ask.get('deadline')}")
    return "\n".join(lines)


async def decide_deadline(message: discord.Message, slug: str, decision: str, new_date: str):
    """Atasan jawab pertanyaan deadline lewat chat: closed -> umumkan hari terakhir + @everyone, extend -> tunggu
    deadline baru di website (perubahannya diumumkan otomatis di channel campaign)."""
    asks = pending_deadlines()
    ask = asks.pop(slug, None)
    if not ask:
        await control_reply(message, "Hmm, campaign yang mana ya? Aku lagi nggak nunggu jawaban deadline buat itu.")
        return
    store.save("deadline_state.json", asks)
    c = watcher.get(slug) or {"slug": slug, "title": slug, "deadline": ask.get("deadline")}
    channel = message.guild.get_channel(ask["channel_id"])
    where = channel.mention if channel else "channel campaign-nya"
    store.activity(kind="deadline_decision", user=str(message.author), user_id=message.author.id, slug=slug,
                   decision=decision, new_date=new_date)
    if decision == "extend":
        until = ""
        if new_date:
            try:
                until = f" sampai {format_value('deadline', datetime.date.fromisoformat(new_date).isoformat())}"
            except ValueError:
                pass
        await control_reply(message, f"Siap, **{c.get('title')}** di-extend{until}. Jangan lupa ubah deadline-nya di "
                                     f"website ya, begitu berubah aku kabari di {where}.")
        return
    if not channel:
        await control_reply(message, f"Channel campaign **{c.get('title')}** nggak ketemu, jadi belum aku umumin.")
        return
    text = random.choice(texts.DEADLINE_H).format(**watcher.announce_facts(c)) if watcher.get(slug) \
        else f"Hari ini hari terakhir **{c.get('title')}**."
    msg = await send(channel, "@everyone " + text, everyone=True)
    store.event("deadline_reminder_sent", slug=slug, reminder="H")
    await control_reply(message, f"Oke, closed sesuai deadline. Udah aku umumin di {where}: {msg.jump_url}")


def budget_line() -> str:
    parts = [f"**{c.get('title')}** {watcher.pct_text(watcher.remaining_pct(c))}"
             for c in watcher.active() if watcher.remaining_pct(c) is not None]
    return ("Sisa budget: " + " · ".join(parts)) if parts else ""


async def daily_text() -> str:
    line = budget_line()
    text = await compose(
        "Pengingat sore buat para clipper: tanya apakah mereka sudah upload klip hari ini, singgung bahwa budget "
        "campaign masih ada (angka detail ditulis terpisah di bawah pesanmu, jadi jangan tulis angka persen), dan "
        "ajak tanya kalau ada kendala. Pendek, 2-3 kalimat, beda dari kemarin.",
        {"tanggal": store.now_wib().strftime("%A %d %B %Y"), "campaign_aktif": len(watcher.active())},
        texts.DAILY_REMINDER, ["upload"])
    return text + (f"\n{line}" if line else "")


@tasks.loop(minutes=5)
async def daily_loop():
    """Pengingat harian ke #diskusi-general. Sebelum aktif, kirim preview dulu ke channel kontrol."""
    guild = home_guild()
    if not guild:
        return
    state = store.load("bot_state.json", {})
    daily = state.setdefault("daily", {})
    channel = general_channel(guild)
    if not daily.get("enabled"):
        if daily.get("preview_id"):
            return
        ctl = control_channel(guild)
        if not ctl or not channel:
            return
        text = await daily_text()
        await send(ctl, f"Contoh pengingat harian yang bakal aku kirim ke {channel.mention} tiap jam "
                        f"{config.DAILY_REMINDER_HOUR}.00 WIB (teksnya ganti tiap hari):")
        msg = await ctl.send(">>> @everyone " + tidy(text), allowed_mentions=discord.AllowedMentions.none())
        await ctl.send("React ✅ di contoh di atas buat aktifin. Kalau belum oke, abaikan aja dulu.")
        await msg.add_reaction("✅")
        daily["preview_id"] = msg.id
        store.save("bot_state.json", state)
        return

    now = store.now_wib()
    today = now.date().isoformat()
    if now.hour < config.DAILY_REMINDER_HOUR or daily.get("last") == today or not channel:
        return
    if not channel.permissions_for(guild.me).mention_everyone:
        await alert(f"Pengingat harian belum bisa tag @everyone di {channel.mention}: role Minhub butuh izin "
                    f"**Mention Everyone**.", key="perm:everyone")
    await send(channel, "@everyone " + await daily_text(), everyone=True)
    daily["last"] = today
    store.save("bot_state.json", state)
    store.event("reminder_sent", channel=channel.name)


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
        guild = home_guild()
        channel = control_channel(guild) if guild else None
        role = admin_role(guild) if guild else None
        if channel:
            await send(channel,
                       f"{role.mention if role else 'Admin'} pengingat rutin: login dulu ke {config.LOGIN_REMINDER_URL} "
                       f"ya (cukup buka dan login). Server gratis Wispbyte dimatikan kalau 2 minggu nggak login, "
                       f"nanti aku ikut mati 😅", roles=True)
            store.event("login_reminder_sent")
        last = today
    with open(REMINDER_FILE, "w", encoding="utf-8") as f:
        json.dump({"last": last.isoformat()}, f)


@tasks.loop(minutes=1)
async def heartbeat_loop():
    state = store.load("bot_state.json", {})
    state["heartbeat"] = store.now_wib().isoformat(timespec="seconds")
    store.save("bot_state.json", state)


for _loop in (campaign_loop, viral_loop, reminder_loop, status_loop, daily_loop):
    @_loop.error
    async def _loop_error(exc, _l=_loop, _name=_loop.coro.__name__):
        """Tugas berkala yang error jangan sampai mati selamanya: lapor admin, nyalakan lagi 1 menit kemudian."""
        log.error("Tugas %s error: %r", _name, exc, exc_info=exc)
        await alert(f"Tugas berkala `{_name}` error: `{type(exc).__name__}: {str(exc)[:300]}`. "
                    f"Aku coba jalanin lagi 1 menit lagi.", key=f"loop:{_name}")
        await asyncio.sleep(60)
        if not _l.is_running():
            _l.start()


if __name__ == "__main__":
    try:
        client.run(os.environ["DISCORD_TOKEN"], log_handler=None)
    finally:
        state = store.load("bot_state.json", {})
        state["clean_stop"] = store.now_wib().isoformat(timespec="seconds")
        store.save("bot_state.json", state)
