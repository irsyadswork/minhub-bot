"""Ingatan jangka panjang Minhub: catatan fakta & preferensi dari admin (lewat "ingat: ...", jawaban admin ke member,
koreksi admin, atau rangkuman mingguan; yang otomatis baru disimpan setelah di-acc). Disimpan di memory.json (ikut
DATA_DIR) dan yang relevan dipakai AI tiap jawab, jadi catatan boleh banyak tanpa bikin prompt bengkak."""
import re

import config
import store

FILE = "memory.json"
PENDING_FILE = "memory_pending.json"  # usulan catatan yang nunggu acc


def notes() -> list[dict]:
    return store.load(FILE, [])


def add(text: str, by: str, source: str = "", slug: str = "") -> dict:
    items = notes()
    next_id = max((n["id"] for n in items), default=0) + 1
    note = {"id": next_id, "text": text.strip()[:500], "by": by, "source": source, "slug": slug,
            "t": store.now_wib().isoformat(timespec="seconds")}
    items.append(note)
    store.save(FILE, items[-config.MEMORY_MAX_NOTES:])
    return note


def remove(ids: list[int]) -> list[dict]:
    items = notes()
    gone = [n for n in items if n["id"] in ids]
    store.save(FILE, [n for n in items if n["id"] not in ids])
    return gone


def existing(ids: list[int]) -> list[dict]:
    return [n for n in notes() if n["id"] in ids]


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w{3,}", (text or "").lower()))


def relevant(query: str = "", slug: str = "", limit: int | None = None) -> list[dict]:
    """Catatan yang paling nyambung sama query/campaign, sisanya diisi catatan terbaru. Urut dari yang paling lama."""
    limit = limit or config.MEMORY_PROMPT_NOTES
    items = notes()
    if len(items) <= limit:
        return items
    words = _words(query)
    scored = []
    for n in items:
        score = len(words & _words(n["text"])) + (3 if slug and n.get("slug") == slug else 0)
        scored.append((score, n["id"], n))
    picked = [n for s, _, n in sorted(scored, key=lambda x: (x[0], x[1]), reverse=True)[:limit * 3 // 4] if s > 0]
    chosen = {n["id"] for n in picked}
    for n in reversed(items):
        if len(picked) >= limit:
            break
        if n["id"] not in chosen:
            picked.append(n)
    return sorted(picked, key=lambda n: n["id"])


def text(query: str = "", slug: str = "", with_ids: bool = False, limit: int | None = None) -> str:
    items = relevant(query, slug, limit)
    if not items:
        return ""
    lines = "\n".join(f"- {'[' + str(n['id']) + '] ' if with_ids else ''}{n['text']} ({n['t'][:10]})" for n in items)
    total = len(notes())
    return lines + (f"\n(ini {len(items)} yang paling nyambung dari total {total} catatan)" if total > len(items) else "")


def stale(active_slugs: set[str]) -> list[dict]:
    """Catatan khusus campaign yang campaign-nya udah nggak aktif."""
    return [n for n in notes() if n.get("slug") and n["slug"] not in active_slugs]


def pending() -> dict:
    return store.load(PENDING_FILE, {})


def save_pending(data: dict):
    store.save(PENDING_FILE, data)


def pending_text() -> str:
    return "\n".join(f"- id: {ask_id} | usulan catatan: {p['text'][:200]}" for ask_id, p in pending().items())
