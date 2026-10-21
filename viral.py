"""Share konten paling meledak dari laporan client ke channel campaign-nya, sekali sehari per campaign.

Aturan:
- Tiap link cuma di-share sekali seumur hidup.
- Pilih konten views terbesar yang belum pernah di-share, minimal VIRAL_MIN_VIEWS (100rb).
- Kalau sudah VIRAL_STUCK_DAYS hari nggak ada yang tembus 100rb, boleh share yang tertinggi asal minimal
  VIRAL_FALLBACK_MIN_VIEWS (20rb).
"""
import json
import os
import random
from datetime import date, datetime, timedelta, timezone

import aiohttp

import config

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viral_state.json")
REPORT_API = "https://laporan.clipperhub.site/api/laporan/"
WIB = timezone(timedelta(hours=7))

TEMPLATES = [
    "@everyone 🔥 Gais ini konten meledak di **{title}**! Viewsnya udah **{views}** di {platform} (by {user}). "
    "Gasskeun ATM dan ikutin yak 👇\n{link}",
    "@everyone 🚀 Ada yang tembus **{views} views** nih di {platform} (by {user})! Amati, tiru, modifikasi, "
    "terus gas upload versi kalian 💪\n{link}",
    "@everyone 💣 Konten **{title}** ini lagi pecah: **{views} views** di {platform} (by {user}). "
    "Pelajari hook-nya, ATM, dan ikutin yak!\n{link}",
]


def _views(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " juta"
    if n >= 1000:
        return f"{n / 1000:.0f}rb"
    return str(n)


def today_wib() -> date:
    return datetime.now(WIB).date()


class ViralSharer:
    def __init__(self):
        self.state = {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, encoding="utf-8") as f:
                self.state = json.load(f)

    def _save(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=1)

    def due(self) -> bool:
        return datetime.now(WIB).hour >= config.VIRAL_POST_HOUR

    async def fetch(self, token: str) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(REPORT_API + token, timeout=aiohttp.ClientTimeout(total=30),
                                   headers={"User-Agent": "Minhub/1.0"}) as r:
                r.raise_for_status()
                data = await r.json(content_type=None)
        return data.get("records") or []

    async def pick(self, slug: str, token: str):
        """Balikin konten yang harus di-share hari ini untuk campaign ini (atau None). Sekali per hari."""
        today = today_wib().isoformat()
        st = self.state.setdefault(slug, {"shared": [], "since": today, "last_big": None, "last_day": None})
        if st["last_day"] == today:
            return None

        records = await self.fetch(token)
        shared = set(st["shared"])
        candidates = sorted((r for r in records if r.get("link") and r["link"] not in shared),
                            key=lambda r: r.get("views") or 0, reverse=True)
        best = candidates[0] if candidates else None
        best_views = (best or {}).get("views") or 0

        stuck_since = date.fromisoformat(st["last_big"] or st["since"])
        stuck_days = (today_wib() - stuck_since).days

        choice = None
        if best_views >= config.VIRAL_MIN_VIEWS:
            choice = best
            st["last_big"] = today
        elif stuck_days >= config.VIRAL_STUCK_DAYS and best_views >= config.VIRAL_FALLBACK_MIN_VIEWS:
            choice = best

        st["last_day"] = today
        if choice:
            st["shared"].append(choice["link"])
        self._save()
        return choice

    def message(self, campaign: dict, rec: dict) -> str:
        user = rec.get("username") or "clipper"
        return random.choice(TEMPLATES).format(
            title=campaign.get("title", "campaign ini"),
            views=_views(int(rec.get("views") or 0)),
            platform=rec.get("platform") or "sosmed",
            user=f"@{user.lstrip('@')}",
            link=rec["link"],
        )
