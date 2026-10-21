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
