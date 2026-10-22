"""Penyimpanan kecil berbasis file: state JSON, log event (buat rekap), dan log aktivitas (siapa/kapan/apa)."""
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WIB = timezone(timedelta(hours=7))
EVENTS_FILE = os.path.join(HERE, "events.jsonl")
ACTIVITY_FILE = os.path.join(HERE, "activity.jsonl")

EVENT_LABELS = {
    "member_join": "member join",
    "welcome_sent": "welcome terkirim",
    "reminder_sent": "pengingat harian terkirim",
    "login_reminder_sent": "pengingat login Wispbyte terkirim",
    "viral_alert_sent": "alert konten viral terkirim",
    "status_alert_sent": "alert status budget terkirim",
    "campaign_announced": "pengumuman campaign baru",
    "campaign_update_sent": "update campaign terkirim",
    "deadline_reminder_sent": "pengingat deadline terkirim",
}


def now_wib() -> datetime:
    return datetime.now(WIB)


def load(name: str, default):
    path = os.path.join(HERE, name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(name: str, data):
    path = os.path.join(HERE, name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def _append(path: str, row: dict):
    row = {"t": now_wib().isoformat(timespec="seconds"), **row}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def event(event_type: str, /, **data):
    _append(EVENTS_FILE, {"type": event_type, **data})


def activity(**data):
    _append(ACTIVITY_FILE, data)


def _read(path: str) -> list[dict]:
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        pass
    return rows


def recap() -> str:
    """Rekap event asli untuk konteks AI. Kalau belum ada data, bilang jelas."""
    rows = _read(EVENTS_FILE)
    if not rows:
        return "BELUM ADA DATA EVENT SAMA SEKALI (pencatatan baru mulai setelah update ini)."
    today = now_wib().date()
    by_day: dict = {}
    names: dict = {}
    for r in rows:
        try:
            day = datetime.fromisoformat(r["t"]).date()
        except (KeyError, ValueError):
            continue
        by_day.setdefault(day, Counter())[r.get("type")] += 1
        if r.get("type") == "welcome_sent" and r.get("user"):
            names.setdefault(day, []).append(r["user"])

    def line(label, days):
        total = Counter()
        for d in days:
            total.update(by_day.get(d, Counter()))
        if not total:
            return f"- {label}: tidak ada event tercatat"
        return f"- {label}: " + ", ".join(f"{EVENT_LABELS.get(k, k)} {v}" for k, v in total.items())

    first = min(by_day)
    out = [
        f"Data dicatat sejak {first.isoformat()} (sebelum itu TIDAK ADA data). Hari ini {today.isoformat()} (WIB).",
        line("Hari ini", [today]),
        line("Kemarin", [today - timedelta(days=1)]),
        line("7 hari terakhir", [today - timedelta(days=i) for i in range(7)]),
    ]
    if names.get(today):
        out.append("- Member yang disambut hari ini: " + ", ".join(names[today][-30:]))
    return "\n".join(out)
