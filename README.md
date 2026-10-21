# Minhub — bot Discord Clipper Hub Circle

Fitur:
- **Welcome + kartu gambar** setiap ada member baru (tag username-nya).
- **Channel otomatis**: bot bikin `#diskusi`, `#minhub-control` (privat admin), dan satu channel diskusi per campaign aktif
  di kategori "Diskusi Campaign 🎬". Campaign baru di website → channel baru otomatis. Slug campaign disimpan di topic channel.
- **Paham konteks**: di channel campaign, bot tahu detail campaign itu (hashtag, min views, deadline, platform, dll.)
  dan membaca ~10 pesan terakhir.
- **Nimbrung pintar**: di `#diskusi` & channel campaign, bot menjawab pertanyaan walau tidak di-tag, tapi diam kalau
  cuma basa-basi/obrolan antar member. Kalau di-tag (atau dibalas), bot selalu jawab.
- **Jeda humanis** 5–60 detik dengan status "typing..." sebelum membalas.
- **Pengumuman campaign baru** dari https://campaign.clipperhub.site (dicek tiap 3 menit) + link campaign & channel diskusinya.
- **Perintah admin** di `#minhub-control`: kirim screenshot + "share ini ke grup ssv, bilang angle baru" → bot kasih
  preview, admin react ✅ → terkirim ke channel campaign itu.

Butuh: Message Content Intent ON (Developer Portal) dan role Minhub punya izin **Manage Channels** + **Manage Roles**.

## Hosting 24/7 (Wispbyte) & cara update
Bot jalan di Wispbyte (server `5579c560`), kodenya ditarik dari repo GitHub ini.
1. Ubah kode di PC → `git commit` → `git push`.
2. Buka https://wispbyte.com/client/servers/5579c560/github → **Pull** → **Pull Changes**.
   Ini menarik kode terbaru lalu menyalakan ulang bot. (Tombol Restart biasa TIDAK menarik kode baru.)

Catatan:
- `.env` (token) tidak ada di GitHub; file itu di-upload manual sekali ke Files Wispbyte.
- Login ke Wispbyte minimal tiap 2 minggu, kalau tidak server dihentikan.
- Jangan jalankan bot di PC bersamaan dengan Wispbyte (balasan jadi dobel).

## Menyalakan bot di PC (untuk tes)
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
