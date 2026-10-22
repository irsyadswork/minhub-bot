"""Share konten paling meledak dari laporan client ke channel campaign-nya, sekali sehari per campaign.

Aturan:
- Tiap link cuma di-share sekali seumur hidup.
- Pilih konten views terbesar yang belum pernah di-share, minimal VIRAL_MIN_VIEWS (100rb).
- Kalau sudah VIRAL_STUCK_DAYS hari nggak ada yang tembus 100rb, boleh share yang tertinggi asal minimal
  VIRAL_FALLBACK_MIN_VIEWS (20rb).
"""
import json
import os
from datetime import date, datetime, timedelta, timezone

import aiohttp

import config

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viral_state.json")
REPORT_API = "https://laporan.clipperhub.site/api/laporan/"
WIB = timezone(timedelta(hours=7))

PLATFORM_NAMES = {"tiktok": "TikTok", "instagram": "Instagram", "youtube": "YouTube", "threads": "Threads",
                  "facebook": "Facebook", "x": "X", "twitter": "X"}


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

    def _st(self, slug: str) -> dict:
        st = self.state.setdefault(slug, {"shared": [], "since": today_wib().isoformat(), "last_big": None,
                                          "last_day": None})
        st.setdefault("rejected", [])
        return st

    def done_today(self, slug: str) -> bool:
        return self._st(slug)["last_day"] == today_wib().isoformat()

    async def candidates(self, slug: str, token: str) -> list[dict]:
        """Konten yang layak diusulkan hari ini, views terbesar dulu. Yang sudah pernah di-share atau pernah
        diganti admin (misal curiga suntik views / link mati) nggak ikut."""
        st = self._st(slug)
        skip = set(st["shared"]) | set(st["rejected"])
        records = sorted((r for r in await self.fetch(token) if r.get("link") and r["link"] not in skip),
                         key=lambda r: r.get("views") or 0, reverse=True)
        stuck_since = date.fromisoformat(st["last_big"] or st["since"])
        stuck = (today_wib() - stuck_since).days >= config.VIRAL_STUCK_DAYS
        minimum = config.VIRAL_FALLBACK_MIN_VIEWS if stuck else config.VIRAL_MIN_VIEWS
        return [r for r in records if (r.get("views") or 0) >= minimum]

    def mark_posted(self, slug: str, rec: dict):
        st = self._st(slug)
        today = today_wib().isoformat()
        st["shared"].append(rec["link"])
        st["last_day"] = today
        if (rec.get("views") or 0) >= config.VIRAL_MIN_VIEWS:
            st["last_big"] = today
        self._save()

    def mark_rejected(self, slug: str, link: str):
        self._st(slug)["rejected"].append(link)
        self._save()

    def mark_skipped(self, slug: str):
        """Hari ini nggak ada yang di-share (nggak ada kandidat, atau admin pilih skip)."""
        self._st(slug)["last_day"] = today_wib().isoformat()
        self._save()

    def facts(self, campaign: dict, rec: dict) -> dict:
        """Data yang wajib disebut di alert: kreator, campaign, platform, views, link."""
        user = rec.get("username") or "clipper"
        platform = str(rec.get("platform") or "sosmed")
        return {
            "title": campaign.get("title", "campaign ini"),
            "views": _views(int(rec.get("views") or 0)),
            "platform": PLATFORM_NAMES.get(platform.lower(), platform),
            "user": f"@{user.lstrip('@')}",
            "link": rec["link"],
        }
