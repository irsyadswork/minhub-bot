"""Ingatan jangka panjang Minhub: catatan fakta dari admin (lewat "ingat: ..." atau jawaban admin ke member yang
di-acc). Disimpan di memory.json (ikut DATA_DIR, jadi aman di Volume Railway) dan dipakai AI tiap jawab."""
import config
import store

FILE = "memory.json"
PENDING_FILE = "memory_pending.json"  # usulan catatan dari jawaban admin yang nunggu acc


def notes() -> list[dict]:
    return store.load(FILE, [])


def add(text: str, by: str, source: str = "") -> dict:
    items = notes()
    next_id = max((n["id"] for n in items), default=0) + 1
    note = {"id": next_id, "text": text.strip()[:500], "by": by, "source": source,
            "t": store.now_wib().isoformat(timespec="seconds")}
    items.append(note)
    store.save(FILE, items[-config.MEMORY_MAX_NOTES:])
    return note


def remove(ids: list[int]) -> list[dict]:
    items = notes()
    gone = [n for n in items if n["id"] in ids]
    store.save(FILE, [n for n in items if n["id"] not in ids])
    return gone


def text(with_ids: bool = False) -> str:
    items = notes()
    if not items:
        return ""
    return "\n".join(f"- {'[' + str(n['id']) + '] ' if with_ids else ''}{n['text']} ({n['t'][:10]})" for n in items)


def pending() -> dict:
    return store.load(PENDING_FILE, {})


def save_pending(data: dict):
    store.save(PENDING_FILE, data)


def pending_text() -> str:
    return "\n".join(f"- id: {ask_id} | usulan catatan: {p['text'][:200]}" for ask_id, p in pending().items())
