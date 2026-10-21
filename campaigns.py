"""Pantau website campaign; kasih tahu kalau ada campaign baru."""
import json
import os
from datetime import date

import aiohttp
import discord

import config

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_campaigns.json")
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _rupiah(n) -> str:
    return "Rp" + f"{int(n or 0):,}".replace(",", ".")


def _tanggal(iso) -> str:
    try:
        d = date.fromisoformat(iso)
        return f"{d.day} {BULAN[d.month - 1]} {d.year}"
    except (TypeError, ValueError):
        return "-"


class CampaignWatcher:
    def __init__(self):
        self.campaigns: list[dict] = []

    def link(self, c: dict) -> str:
        return f"{config.CAMPAIGN_SITE}/campaigns/{c['slug']}"

    async def fetch(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.CAMPAIGN_SITE}/api/data", timeout=aiohttp.ClientTimeout(total=20)) as r:
                r.raise_for_status()
                data = await r.json()
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

    def channel_name(self, c: dict) -> str:
        return (config.CAMPAIGN_CHANNEL_PREFIX + c["slug"])[:100]

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
            )
        return "\n".join(lines)

    def announcement(self, c: dict) -> tuple[str, discord.Embed]:
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
        image = (c.get("poster") or {}).get("image")
        if image:
            embed.set_image(url=image if image.startswith("http") else config.CAMPAIGN_SITE + image)
        embed.set_footer(text=config.SERVER_NAME)

        text = f"{config.CAMPAIGN_TEXT}\n🔗 {url}"
        return text, embed
