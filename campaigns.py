"""Pantau website campaign: campaign baru, sisa budget, dan perubahan data campaign."""
import json
import os
from datetime import date

import aiohttp
import discord

import config

STATE_FILE = os.path.join(config.DATA_DIR, "seen_campaigns.json")
STATUS_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
# Field yang dipantau perubahannya (dikabarkan di channel campaign-nya)
TRACKED = {
    "title": "Nama campaign", "rate": "Rate", "deadline": "Deadline", "minViews": "Min. views",
    "minViewsMode": "Mode min. views", "maxViewsPerVideo": "Maks. views dihitung per video",
    "maxVideoKirim": "Maks. video dikirim", "platforms": "Platform", "hashtags": "Hashtag wajib",
    "tagline": "Tagline", "lookingFor": "Yang dicari", "dos": "Do's", "donts": "Don'ts", "hooks": "Ide hook",
    "extraRules": "Aturan tambahan", "about": "Tentang/brief", "payMode": "Sistem bayar",
}
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _rupiah(n) -> str:
    return "Rp" + f"{int(n or 0):,}".replace(",", ".")


def _tanggal(iso) -> str:
    try:
        d = date.fromisoformat(iso)
        return f"{d.day} {BULAN[d.month - 1]} {d.year}"
    except (TypeError, ValueError):
        return "-"


def _item(i) -> str:
    return str(i if not isinstance(i, dict) else i.get("text") or i.get("judul") or i)


def format_value(key: str, v) -> str:
    if v in (None, "", []):
        return "-"
    if key == "rate":
        return f"{_rupiah(v)} / 1K views"
    if key == "deadline":
        return _tanggal(v)
    if key in ("minViews", "maxViewsPerVideo"):
        return f"{int(v):,}".replace(",", ".")
    if isinstance(v, list):
        return ", ".join(_item(i) for i in v)
    return str(v)


class CampaignWatcher:
    def __init__(self):
        self.campaigns: list[dict] = []
        self.live: dict = {}

    def link(self, c: dict) -> str:
        return f"{config.CAMPAIGN_SITE}/campaigns/{c['slug']}"

    async def fetch(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.CAMPAIGN_SITE}/api/data", timeout=aiohttp.ClientTimeout(total=20)) as r:
                r.raise_for_status()
                data = await r.json()
        self.live = data.get("live") or {}
        deleted = set((data.get("admin") or {}).get("deleted") or [])
        self.campaigns = [
            c for c in (data.get("admin") or {}).get("created") or []
            if c.get("slug") and c["slug"] not in deleted
        ]
        return self.campaigns

    async def check_new(self) -> list[dict]:
        """Ambil data terbaru, balikin campaign aktif yang belum pernah diumumkan.
        Pertama kali jalan: semua campaign yang sudah ada dianggap 'lama' supaya nggak spam."""
        await self.fetch()
        first_run = not os.path.exists(STATE_FILE)
        seen = set()
        if not first_run:
            with open(STATE_FILE, encoding="utf-8") as f:
                seen = set(json.load(f))

        new = [c for c in self.campaigns if c["slug"] not in seen and c.get("status", "aktif") == "aktif"]
        seen |= {c["slug"] for c in self.campaigns}
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(seen), f, indent=2)
        return [] if first_run else new

    def active(self) -> list[dict]:
        return [c for c in self.campaigns if c.get("status", "aktif") == "aktif"]

    def get(self, slug: str):
        return next((c for c in self.campaigns if c["slug"] == slug), None)

    # --- Channel diskusi per campaign. Slug disimpan di topic channel biar bot tahu channel itu campaign apa. ---
    TOPIC_TAG = "campaign:"

    # --- Sisa budget, rumusnya sama dengan website: (budget - paid) / budget ---
    def remaining_pct(self, c: dict):
        budget = c.get("budget") or 0
        if budget <= 0:
            return None
        paid = (self.live.get(c["slug"]) or {}).get("paid", c.get("paid") or 0) or 0
        return max(0, budget - paid) / budget * 100

    @staticmethod
    def budget_status(pct) -> str | None:
        if pct is None:
            return None
        if pct <= 0:
            return "red"
        return "yellow" if pct <= config.BUDGET_YELLOW_PCT else "green"

    @staticmethod
    def pct_text(pct) -> str:
        if pct is None:
            return "-"
        if 0 < pct < 1:
            return "<1%"
        return f"{round(pct)}%"

    def status_of(self, c: dict) -> str | None:
        return self.budget_status(self.remaining_pct(c))

    def channel_name(self, c: dict, status: str | None = None) -> str:
        emoji = STATUS_EMOJI.get(status or self.status_of(c) or "green")
        return (emoji + config.CAMPAIGN_CHANNEL_SEPARATOR + c["slug"])[:100]

    def poster(self, c: dict) -> str | None:
        image = (c.get("poster") or {}).get("image")
        if not image:
            return None
        return image if image.startswith("http") else config.CAMPAIGN_SITE + image

    # --- Perubahan data campaign ---
    @staticmethod
    def snapshot(c: dict) -> dict:
        return {k: c.get(k) for k in TRACKED}

    @staticmethod
    def diff(old: dict, new: dict) -> list[str]:
        """Baris "Field: sebelum → sesudah". List panjang ditulis sebagai yang ditambah/dihapus."""
        lines = []
        for key, label in TRACKED.items():
            a, b = old.get(key), new.get(key)
            if a == b or (a in (None, "", []) and b in (None, "", [])):
                continue
            if isinstance(a, list) and isinstance(b, list) and (len(a) > 3 or len(b) > 3):
                sa, sb = [_item(i) for i in a], [_item(i) for i in b]
                added = [i for i in sb if i not in sa]
                removed = [i for i in sa if i not in sb]
                parts = []
                if added:
                    parts.append("ditambah: " + "; ".join(added))
                if removed:
                    parts.append("dihapus: " + "; ".join(removed))
                lines.append(f"**{label}**: " + (" | ".join(parts) or "urutan diubah"))
            else:
                lines.append(f"**{label}**: {format_value(key, a)} → {format_value(key, b)}")
        return lines

    def channel_topic(self, c: dict) -> str:
        return f"Diskusi {c.get('title')} · brief: {self.link(c)} · {self.TOPIC_TAG}{c['slug']}"[:1024]

    def slug_from_topic(self, topic) -> str | None:
        if topic and self.TOPIC_TAG in topic:
            return topic.split(self.TOPIC_TAG, 1)[1].split()[0].strip()
        return None

    def detail(self, c: dict) -> str:
        """Detail lengkap satu campaign untuk konteks AI di channel campaign itu."""
        def daftar(key):
            items = c.get(key) or []
            return "; ".join(str(i if not isinstance(i, dict) else i.get("text") or i.get("judul") or i) for i in items) or "-"

        return "\n".join([
            f"CHANNEL INI KHUSUS CAMPAIGN: {c.get('title')} (brand {c.get('brand')}, kategori {c.get('category')})",
            f"- Tagline: {c.get('tagline') or '-'}",
            f"- Link brief/detail & join: {self.link(c)}",
            f"- Status: {c.get('status')} | Deadline: {_tanggal(c.get('deadline'))}",
            f"- Bayaran: {_rupiah(c.get('rate'))} per 1.000 views ({c.get('payMode')})",
            f"- Minimal views: {int(c.get('minViews') or 0):,} ({c.get('minViewsMode') or '-'})".replace(",", "."),
            f"- Maksimal views dihitung per video: {int(c.get('maxViewsPerVideo') or 0):,}".replace(",", "."),
            f"- Maksimal video yang boleh dikirim: {c.get('maxVideoKirim') or '-'}",
            f"- Platform: {', '.join(c.get('platforms') or []) or '-'}",
            f"- Hashtag wajib: {' '.join(c.get('hashtags') or []) or '-'}",
            f"- Yang dicari: {daftar('lookingFor')}",
            f"- Do's: {daftar('dos')}",
            f"- Don'ts: {daftar('donts')}",
            f"- Ide hook: {daftar('hooks')}",
            f"- Aturan tambahan: {daftar('extraRules')}",
            f"- Tentang: {daftar('about')}",
            "Kalau ditanya hal yang nggak ada di atas, arahkan cek brief di link di atas atau tag admin.",
        ])

    def summary(self) -> str:
        """Ringkasan campaign aktif untuk konteks AI."""
        lines = []
        for c in self.campaigns:
            if c.get("status", "aktif") != "aktif":
                continue
            lines.append(
                f"- {c.get('title')} (slug: {c['slug']}) | brand {c.get('brand')} | {c.get('category')} | "
                f"{_rupiah(c.get('rate'))}/1K views | deadline {_tanggal(c.get('deadline'))} | "
                f"platform: {', '.join(c.get('platforms') or [])} | tagline: {c.get('tagline')}"
                + (f" | sering disebut member: {', '.join(config.CAMPAIGN_ALIASES[c['slug']])}"
                   if c["slug"] in config.CAMPAIGN_ALIASES else "")
            )
        return "\n".join(lines)

    def intro(self, c: dict) -> tuple[str, discord.Embed]:
        """Pesan pembuka (di-pin) di channel diskusi campaign: teks + kartu dengan banner campaign."""
        url = self.link(c)
        text = (f"Ini tempat diskusi **{c.get('title')}**.\n"
                f"Brief & join: <{url}>\n"
                f"Bingung soal campaign ini? Tanya aja di sini, {config.BOT_NAME} standby.")
        embed = discord.Embed(title=c.get("title"), url=url, description=c.get("tagline") or None, color=0x488CFF)
        embed.add_field(name="💰 Rate", value=f"{_rupiah(c.get('rate'))} / 1K views", inline=True)
        embed.add_field(name="⏰ Deadline", value=_tanggal(c.get("deadline")), inline=True)
        if c.get("hashtags"):
            embed.add_field(name="#️⃣ Hashtag wajib", value=" ".join(c["hashtags"]), inline=False)
        if self.poster(c):
            embed.set_image(url=self.poster(c))
        embed.set_footer(text=config.SERVER_NAME)
        return text, embed

    def announcement(self, c: dict) -> discord.Embed:
        url = self.link(c)
        embed = discord.Embed(title=c.get("title", "Campaign baru"), url=url,
                              description=c.get("tagline") or None, color=0x488CFF)
        embed.add_field(name="🏷️ Brand", value=c.get("brand") or "-", inline=True)
        embed.add_field(name="💰 Rate", value=f"{_rupiah(c.get('rate'))} / 1K views", inline=True)
        embed.add_field(name="🎯 Kategori", value=c.get("category") or "-", inline=True)
        embed.add_field(name="⏰ Deadline", value=_tanggal(c.get("deadline")), inline=True)
        if c.get("minViews"):
            embed.add_field(name="👀 Min. views", value=f"{int(c['minViews']):,}".replace(",", "."), inline=True)
        if c.get("platforms"):
            embed.add_field(name="📱 Platform", value=", ".join(p.capitalize() for p in c["platforms"]), inline=True)
        if self.poster(c):
            embed.set_image(url=self.poster(c))
        embed.set_footer(text=config.SERVER_NAME)
        return embed

    def announce_facts(self, c: dict) -> dict:
        return {"title": c.get("title", "campaign baru"), "brand": c.get("brand") or "-",
                "rate": f"{_rupiah(c.get('rate'))} per 1.000 views", "deadline": _tanggal(c.get("deadline")),
                "link": self.link(c)}
