# Minhub — bot Discord Clipper Hub Circle

Fitur:
- **Welcome + kartu gambar** setiap ada member baru (tag username-nya).
- **Jawab pertanyaan** kalau bot di-tag di channel diskusi. Pertanyaan basic dijawab langsung; yang teknis (payout, aturan detail, error akun) diarahkan ke brief/rules dan tag admin.
- **Jeda humanis** 5–60 detik dengan status "typing..." sebelum membalas.
- **Pengumuman campaign baru** dari https://campaign.clipperhub.site (dicek tiap 3 menit) + link campaign-nya.

## Menyalakan bot
Double-click **`jalankan-bot.bat`**, atau jalankan:
```
python bot.py
```
Bot online selama jendela itu terbuka.

## File penting
| File | Isi |
|---|---|
| `.env` | Token Discord + API key Gemini (RAHASIA) |
| `config.py` | Nama channel, role admin, teks welcome, teks pengumuman campaign, jeda balasan |
| `faq.md` | FAQ yang dipakai bot untuk menjawab — makin lengkap makin pintar |
| `assets/background.webp` | Background kartu welcome |
| `seen_campaigns.json` | Daftar campaign yang sudah pernah diumumkan (otomatis) |

## Alat bantu
- `python cek_server.py` — cek bot sudah masuk server dan nama channel/role di `config.py` cocok.
- `python preview_welcome.py` — bikin `preview_welcome.png` untuk lihat kartu welcome.

## Catatan
- Pertama kali jalan, campaign yang sudah ada **tidak** diumumkan (biar nggak spam). Hanya campaign yang dibuat setelahnya.
- Di Discord Developer Portal → Bot, **Server Members Intent** dan **Message Content Intent** wajib ON.
- Role admin harus bisa di-mention (atau bot punya izin *Mention Everyone*) supaya tag admin berfungsi.
