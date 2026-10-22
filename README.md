# Minhub — bot Discord Clipper Hub Circle

Fitur:
- **Welcome + kartu gambar** setiap ada member baru (tag username-nya). Teksnya dipilih random dari 18 variasi di `texts.py`.
- **Channel otomatis**: satu channel diskusi per campaign aktif di kategori "Diskusi Campaign". Campaign baru di website →
  channel baru otomatis. Channel dikenali pakai ID (aman walau di-rename); slug campaign juga disimpan di topic channel.
- **Status budget di nama channel campaign**: 🟢 sisa > 5%, 🟡 sisa > 0–5%, 🔴 habis. Dicek tiap 30 menit, rename cuma
  kalau status berubah. Perubahan status dilaporkan ke `#minhub-control`; kalau jadi 🔴, member di channel itu dikabari.
- **Update campaign**: kalau rate, deadline, min. views, platform, hashtag, brief, dll. berubah di website, Minhub kabari
  di channel campaign itu (sebelum → sesudah). Plus pengingat deadline H-1 dan hari H (jam 09.00 WIB).
- **Paham konteks**: di channel campaign, bot tahu detail campaign itu (hashtag, min views, deadline, platform, dll.)
  dan membaca ~10 pesan terakhir (pesan error lama Minhub nggak ikut dibaca).
- **Nimbrung pintar**: di `#diskusi-general` & channel campaign, bot menjawab pertanyaan walau tidak di-tag, tapi diam
  kalau cuma basa-basi/obrolan antar member. Kalau di-tag (atau dibalas), bot selalu jawab.
- **Jeda humanis** 5–60 detik dengan status "typing..." sebelum membalas.
- **Pengumuman campaign baru** di `#pengumuman` (dicek tiap 3 menit): tag @everyone, teks variatif (nama, brand, rate,
  deadline, channel diskusi) + kartu campaign.
- **Konten viral** dari laporan client (sekali sehari per campaign mulai 19.00 WIB): selalu dengan kartu preview buatan
  sendiri (thumbnail, caption, akun, platform, views, link). Kalau preview gagal, dilaporkan ke admin dulu.
- **Pengingat harian 17.00 WIB** di `#diskusi-general`: tag @everyone, teks ditulis AI tiap hari + sisa budget tiap campaign.
  Aktif setelah admin react ✅ di contoh yang dikirim ke `#minhub-control`.
- **Perintah admin** di `#minhub-control`: misal *"@Minhub di #pengumuman umumin ... + link"*. Channel tujuan diambil dari
  mention channel; kalau nggak disebut, Minhub nanya dulu. Selalu ada preview persis + konfirmasi ✅ sebelum dikirim.
  Bisa juga *"kirim preview dulu ke sini"* dan tanya rekap (*"berapa member yang disambut hari ini?"*).
- **Preview link aman**: sebelum kirim link, Minhub cek og:image-nya. Kalau rusak, preview bawaan Discord dimatikan
  dan diganti kartu buatan sendiri dengan gambar valid.

Keamanan & monitoring:
- Gemini kena 503/429/timeout → dicoba ulang + pindah model; kalau tetap gagal, member dikasih tahu "lagi rame".
- Error apa pun dilaporkan ke `#minhub-control` dengan alasan aslinya. Bot nyala/restart/crash juga dilaporkan
  (beserta host-nya, jadi ketahuan kalau ada Minhub dobel jalan di PC).
- Rate limit per member, deteksi prompt injection, alert aktivitas mencurigakan ke `#minhub-control`.
- Bot otomatis keluar kalau dimasukkan ke server selain Clipper Hub Circle (`GUILD_ID` di `config.py`).
- Log aktivitas di `activity.jsonl` (siapa, kapan, apa), log event untuk rekap di `events.jsonl`.

Butuh: Server Members Intent + Message Content Intent ON (Developer Portal). Izin role Minhub lihat bagian "Izin bot".

## Hosting 24/7 (Wispbyte) & cara update
Bot jalan di Wispbyte (server `5579c560`), kodenya ditarik dari repo GitHub ini (branch `main`).
1. Ubah kode di PC → `git commit` → `git push`.
2. Buka https://wispbyte.com/client/servers/5579c560/github → **Pull** → **Pull Changes**.
   Ini menarik kode terbaru lalu menyalakan ulang bot. (Tombol Restart biasa TIDAK menarik kode baru.)
3. Cek `#minhub-control`: Minhub kirim "nyala lagi di Wispbyte (versi `xxxxxxx`)". Versi itu harus sama dengan
   commit terakhir di GitHub.

Catatan:
- `.env` (token) tidak ada di GitHub; file itu di-upload manual sekali ke Files Wispbyte.
- Server Wispbyte nggak "tidur" walau sepi (beda dengan Replit/Render gratis), jadi nggak perlu keep-alive ping.
  Yang bikin mati cuma: nggak login ke Wispbyte 2 minggu (Minhub ngingetin tiap 12 hari) atau crash (dilaporkan).
- Jangan jalankan bot di PC bersamaan dengan Wispbyte (balasan jadi dobel).

## Izin bot (seminimal mungkin)
- Server-wide (role Minhub): View Channels, Send Messages, Embed Links, Attach Files, Read Message History,
  Add Reactions, Mention Everyone, Pin Messages.
- Khusus kategori "Diskusi Campaign" (permission overwrite untuk role Minhub): **Manage Channels** + **Manage Permissions**
  (buat bikin channel campaign baru dan ganti emoji status di namanya).
- Nggak perlu Manage Channels / Manage Roles di level server.

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
| `config.py` | ID server/channel/role, jam pengingat, batas rate limit, model Gemini, dll. |
| `texts.py` | Template teks: welcome, cadangan pengingat/pengumuman/alert viral, update campaign |
| `faq.md` | FAQ yang dipakai bot untuk menjawab — makin lengkap makin pintar |
| `assets/background.webp` | Background kartu welcome |
| `seen_campaigns.json`, `campaign_state.json`, `bot_state.json` | State otomatis (jangan diedit manual) |
| `events.jsonl`, `activity.jsonl` | Log event (buat rekap) & log aktivitas |

## Alat bantu
- `python cek_server.py` — cek bot sudah masuk server dan nama channel/role di `config.py` cocok.
- `python preview_welcome.py` — bikin `preview_welcome.png` untuk lihat kartu welcome.

## Catatan
- Pertama kali jalan, campaign yang sudah ada **tidak** diumumkan (biar nggak spam). Hanya campaign yang dibuat setelahnya.
- Role admin harus bisa di-mention (atau bot punya izin *Mention Everyone*) supaya tag admin berfungsi.
