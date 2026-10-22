"""Penyaring gaya bahasa untuk SEMUA teks pesan Minhub (bukan label field embed).
- Buang kata yang dilarang (bestie, gas pol, guys, gas join).
- Emoji maksimal 1, dan cuma dari daftar yang umum dipakai orang. Sisanya dihapus."""
import re

ALLOWED_EMOJI = ["😅", "😂", "🙏", "👍", "👀", "📈"]

_WORDS = [
    (r"\bgas\s*pol+\b[,!]*", ""),
    (r"\bgas+\s+join\b", "join"),
    (r"\bbestie+s?\b[,!]*", ""),
    (r"\bgu+ys\b", "semua"),
    (r"\bgais\b", "semua"),
]

# Emoji: simbol bergambar + modifier warna kulit, variation selector, ZWJ, keycap, bendera.
_EMOJI = re.compile(
    "(?:[\U0001F1E6-\U0001F1FF]{2})"
    "|(?:[#*0-9]️?⃣)"
    "|(?:[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿←-⇿〰〽㊗㊙]"
    "[\U0001F3FB-\U0001F3FF]?️?(?:‍[\U0001F000-\U0001FAFF☀-➿][\U0001F3FB-\U0001F3FF]?️?)*)"
)


def tidy(text: str) -> str:
    if not text:
        return text
    for pattern, repl in _WORDS:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    kept = False

    def keep_first_allowed(m):
        nonlocal kept
        e = m.group(0).replace("️", "")
        if not kept and e in ALLOWED_EMOJI:
            kept = True
            return m.group(0)
        return ""

    text = _EMOJI.sub(keep_first_allowed, text)
    # rapikan sisa spasi/tanda baca setelah kata atau emoji dibuang
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([,.!?])", r"\1", text)
    text = re.sub(r"([,!?])\1+", r"\1", text)
    text = re.sub(r"^[ ,]+|(?<=\n)[ ,]+", "", text)
    return text.strip()
