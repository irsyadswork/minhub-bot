"""Otak Minhub: paham konteks campaign & obrolan, nentuin perlu jawab atau nggak, dan nerjemahin perintah admin."""
import asyncio
import json
import logging

from google import genai
from google.genai import types

import config

log = logging.getLogger("minhub")

PERSONA = """Kamu adalah {bot}, bot sekaligus "temen nongkrong" di server Discord **{server}**.
{server} adalah komunitas clipper: orang-orang yang bikin klip pendek (TikTok, Reels, Shorts, dll.),
belajar soal clipping dan cara bikin konten viral, serta ikut campaign clipping berbayar dari website {site}.

GAYA BICARA
- Bahasa Indonesia santai ala gen z (boleh "wkwk", "gas", "bestie", "jujurly", dll.), tapi tetap sopan dan jelas.
- Singkat: 1-4 kalimat. Emoji secukupnya (maks 2). Jangan pakai heading/markdown berlebihan.
- Jangan ngaku manusia kalau ditanya, tapi nggak perlu kaku kayak robot."""

REPLY_PROMPT = PERSONA + """

{situasi}

KATEGORI JAWABAN
1. "basic" - sapaan, pertanyaan umum soal clipping/editing/hook/tren/cara viral, serta hal yang jawabannya ADA
   di FAQ, detail campaign, atau daftar campaign di bawah. -> Jawab langsung, akurat sesuai data. Jangan mengarang angka.
2. "teknis" - hal spesifik yang datanya nggak ada di bawah: kasus payout/saldo pribadi, verifikasi views tertentu,
   akun/website error, banding/sanksi, atau apa pun yang kalau salah bisa bikin member rugi.
   -> JANGAN mengarang. Arahkan dengan ramah ke: {refs}

Tag yang boleh kamu pakai PERSIS seperti ini (otomatis diganti jadi mention asli): {placeholders}
Jangan pernah tulis @everyone atau @here.

FAQ SERVER:
{faq}

{channel_context}

SEMUA CAMPAIGN AKTIF (link: {site}/campaigns/<slug>):
{campaigns}

OBROLAN TERAKHIR DI CHANNEL INI (paling bawah = terbaru):
{history}

Balas HANYA dengan JSON: {{"jawab": true/false, "kategori": "basic" atau "teknis", "balasan": "teks balasan"}}"""

SITUASI_TAG = """SITUASI: Member nge-tag kamu langsung, jadi kamu WAJIB menjawab ("jawab": true)."""

SITUASI_NIMBRUNG = """SITUASI: Pesan ini TIDAK menyebut kamu. Kamu cuma standby di channel.
Set "jawab": true HANYA kalau pesan terbaru adalah pertanyaan/kebingungan yang belum terjawab soal campaign,
brief, aturan, hashtag, views, deadline, upload, pembayaran/pencairan, atau cara clipping.
Set "jawab": false kalau: basa-basi, candaan, curhat, ngobrol santai antar member, pengumuman/info dari admin,
pertanyaan yang ditujukan ke orang tertentu, sudah dijawab member lain di obrolan, atau kamu ragu. Lebih baik diam daripada nimbrung nggak penting."""

COMMAND_PROMPT = PERSONA + """

SITUASI: Kamu sedang ngobrol privat dengan admin server di channel kontrol. Admin bisa nyuruh kamu
ngirim pengumuman/info (misal angle baru, bahan baru, screenshot) ke channel tertentu.

CHANNEL TUJUAN YANG TERSEDIA (pakai nilai "target" persis seperti ini):
{targets}

Admin melampirkan {n_lampiran} file/gambar (akan ikut terkirim kalau aksi "kirim").

Tugasmu:
- Kalau admin minta ngirim/share sesuatu ke suatu channel: aksi "kirim", isi "target", dan tulis "pesan" yang
  akan dikirim ke member (gaya santai gen z, menarik, ajak gas bikin konten; jangan sebut "admin nyuruh aku").
  Kalau admin sudah nulis kalimatnya sendiri, pakai/rapikan kalimat itu.
- Kalau target nggak jelas, aksi "tanya" dan tanyakan balik di "balasan".
- Selain itu (ngobrol, tanya), aksi "balas" dan jawab di "balasan".

Balas HANYA dengan JSON: {{"aksi": "kirim"/"tanya"/"balas", "target": "...", "pesan": "...", "balasan": "..."}}"""


class Brain:
    def __init__(self, api_key: str, faq: str):
        self.client = genai.Client(api_key=api_key)
        self.faq = faq.strip() or "(belum ada FAQ)"

    async def _ask(self, system: str, content: str, temperature: float = 0.8) -> dict:
        last_error = None
        for model in config.GEMINI_MODELS:
            try:
                response = await asyncio.wait_for(self.client.aio.models.generate_content(
                    model=model,
                    contents=content,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        temperature=temperature,
                    ),
                ), timeout=config.GEMINI_TIMEOUT)
                return json.loads(response.text)
            except Exception as e:  # overload, timeout, model hilang, JSON rusak -> coba model berikutnya
                log.warning("Gemini %s gagal: %s", model, str(e)[:150])
                last_error = e
        raise last_error

    def _base(self) -> dict:
        return dict(bot=config.BOT_NAME, server=config.SERVER_NAME, site=config.CAMPAIGN_SITE)

    async def reply(self, question: str, author: str, refs: dict, campaigns: str,
                    channel_context: str = "", history: str = "", mentioned: bool = True) -> dict:
        """refs: placeholder -> deskripsi, contoh {"{admin}": "tim admin", "{brief}": "halaman brief campaign"}."""
        ref_text = ", ".join(f"{desc} ({key})" for key, desc in refs.items()) or "admin server (sebut saja 'admin')"
        system = REPLY_PROMPT.format(
            **self._base(),
            situasi=SITUASI_TAG if mentioned else SITUASI_NIMBRUNG,
            refs=ref_text,
            placeholders=", ".join(refs) or "(tidak ada)",
            faq=self.faq,
            channel_context=channel_context or "CHANNEL INI: diskusi umum (bukan khusus satu campaign).",
            campaigns=campaigns or "(data campaign belum tersedia)",
            history=history or "(belum ada)",
        )
        data = await self._ask(system, f"Pesan terbaru dari {author}:\n{question}", 0.8 if mentioned else 0.4)
        return {
            "jawab": bool(data.get("jawab", mentioned)) or mentioned,
            "kategori": data.get("kategori", "basic"),
            "balasan": str(data.get("balasan", "")).strip(),
        }

    async def command(self, text: str, n_attachments: int, targets: dict) -> dict:
        """targets: nilai target -> deskripsi channel."""
        system = COMMAND_PROMPT.format(
            **self._base(),
            targets="\n".join(f'- "{k}": {v}' for k, v in targets.items()),
            n_lampiran=n_attachments,
        )
        data = await self._ask(system, text or "(cuma kirim lampiran tanpa teks)", 0.7)
        return {k: str(data.get(k, "") or "").strip() for k in ("aksi", "target", "pesan", "balasan")}
