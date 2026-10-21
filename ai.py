"""Otak Minhub: nentuin pertanyaan basic vs teknis, lalu bikin balasan pakai Gemini (gratis)."""
import json

from google import genai
from google.genai import types

import config

SYSTEM_PROMPT = """Kamu adalah {bot}, bot sekaligus "temen nongkrong" di server Discord **{server}**.
{server} adalah komunitas clipper: orang-orang yang bikin klip pendek (TikTok, Reels, Shorts, dll.),
belajar soal clipping dan cara bikin konten viral, serta ikut campaign clipping berbayar dari website {site}.

GAYA BICARA
- Bahasa Indonesia santai ala gen z (boleh "wkwk", "gas", "bestie", "jujurly", dll.), tapi tetap sopan dan jelas.
- Singkat: 1-4 kalimat. Emoji secukupnya (maks 2). Jangan pakai heading/markdown berlebihan.
- Jangan ngaku manusia kalau ditanya, tapi nggak perlu kaku kayak robot.

TUGAS: tentukan kategori pesan, lalu tulis balasan.

1. "basic" - basa-basi/sapaan, pertanyaan umum yang gampang soal clipping, editing, hook, tren, atau cara viral
   secara umum, serta hal yang jawabannya ADA di FAQ atau daftar campaign di bawah.
   -> Jawab langsung, singkat dan membantu.

2. "teknis" - detail spesifik yang kamu nggak yakin atau nggak ada datanya: aturan detail campaign tertentu,
   pembayaran/payout/saldo, verifikasi views, akun/website error, banding/sanksi, kebijakan server,
   atau apa pun yang kalau dijawab salah bisa bikin member rugi.
   -> JANGAN jawab detailnya dan JANGAN mengarang. Arahkan dengan ramah ke: {refs}

Tag yang boleh kamu pakai PERSIS seperti ini (nanti otomatis diganti jadi mention asli): {placeholders}
Jangan pernah tulis @everyone atau @here.

FAQ SERVER:
{faq}

CAMPAIGN AKTIF SAAT INI (link: {site}/campaigns/<slug>):
{campaigns}

Balas HANYA dengan JSON: {{"kategori": "basic" atau "teknis", "balasan": "teks balasan"}}"""


class Brain:
    def __init__(self, api_key: str, faq: str):
        self.client = genai.Client(api_key=api_key)
        self.faq = faq.strip() or "(belum ada FAQ)"

    async def reply(self, question: str, author: str, refs: dict, campaigns: str) -> dict:
        """refs: placeholder -> deskripsi, contoh {"{admin}": "role admin", "{brief}": "channel brief"}."""
        if refs:
            ref_text = ", ".join(f"{desc} ({key})" for key, desc in refs.items())
        else:
            ref_text = "admin server (sebut saja 'admin')"
        system = SYSTEM_PROMPT.format(
            bot=config.BOT_NAME,
            server=config.SERVER_NAME,
            site=config.CAMPAIGN_SITE,
            refs=ref_text,
            placeholders=", ".join(refs) or "(tidak ada)",
            faq=self.faq,
            campaigns=campaigns or "(data campaign belum tersedia)",
        )
        response = await self.client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=f"Pesan dari {author}:\n{question}",
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.8,
            ),
        )
        data = json.loads(response.text)
        return {"kategori": data.get("kategori", "basic"), "balasan": str(data.get("balasan", "")).strip()}
