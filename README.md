# Minhub — bot Discord Clipper Hub Circle

Fitur:
- **Welcome + kartu gambar** setiap ada member baru (tag username-nya). Teksnya dipilih random dari 18 variasi di `texts.py`.
- **Channel otomatis**: satu channel diskusi per campaign aktif di kategori "Diskusi Campaign". Campaign baru di website →
  channel baru otomatis. Channel dikenali pakai ID (aman walau di-rename); slug campaign juga disimpan di topic channel.
- **Status budget di nama channel campaign**: 🟢 sisa > 5%, 🟡 sisa > 0–5%, 🔴 habis. Dicek tiap 30 menit, rename cuma
  kalau status berubah. Perubahan status dilaporkan ke `#minhub-control`; kalau jadi 🔴, member di channel itu dikabari.
- **Kategori terpisah**: channel campaign 🔴 otomatis dipindah ke kategori `Campaign Closed`, dan balik ke kategori aktif
  kalau statusnya hidup lagi (misal di-extend).
- **Update campaign**: kalau rate, deadline, min. views, platform, hashtag, brief, dll. berubah di website, Minhub kabari
  di channel campaign itu (sebelum → sesudah). Plus pengingat deadline H-1 dan hari H (jam 09.00 WIB).
- **Paham konteks**: di channel campaign, bot tahu detail campaign itu (hashtag, min views, deadline, platform, dll.)
  dan membaca ~10 pesan terakhir (pesan error lama Minhub nggak ikut dibaca).
- **Nimbrung pintar**: di `#diskusi-general` & channel campaign, bot menjawab pertanyaan walau tidak di-tag, tapi diam
  kalau cuma basa-basi/obrolan antar member. Kalau di-tag (atau dibalas), bot selalu jawab.
- **Dua level otak**: jawaban buat member yang nge-tag/bales Minhub dan perintah admin pakai model pintar
  (`gemini-3.5-flash` + mode mikir), keputusan nimbrung & teks otomatis pakai model ringan. Atur di `config.py`
  (`GEMINI_MODELS_SMART`, `GEMINI_MODELS_FAST`, `GEMINI_THINKING`).
- **Baca gambar**: screenshot/gambar dari member (kalau nanya) dan dari admin di `#minhub-control` ikut dibaca AI
  (maks `MAX_IMAGES` gambar, `MAX_IMAGE_MB` MB).
- **Ingatan jangka panjang** (`memory.json`): admin bisa bilang *"ingat: payout siti tiap Jumat"*, *"kamu inget apa
  aja?"*, atau *"lupain catatan nomor 3"* di `#minhub-control`. Muat sampai `MEMORY_MAX_NOTES` catatan; tiap jawab
  dia baca yang paling nyambung (`MEMORY_PROMPT_NOTES`) dan catatan diprioritaskan di atas FAQ.
- **Terus belajar**: jawaban admin ke member (pakai Reply atau nggak), koreksi/penolakan admin, dan rangkuman obrolan
  diusulin jadi catatan. Semua usulan baru disimpan setelah di-acc ✅ (atau dibalas revisinya), jadi member nggak bisa
  ngajarin yang salah. Kalau catatan baru bentrok sama yang lama, atau catatan campaign yang udah selesai, admin ditanya.
- **Kritis & tanya balik**: perintah admin dicek ke data campaign & catatan; kalau beda atau berisiko, Minhub kasih
  saran dulu, keputusan tetap di admin. Kalau bingung atau datanya nggak ada, dia nanya balik. Kalau ragu pas jawab
  member, dia juga nanya ke `#minhub-control`.
- **Rangkuman obrolan member**: tiap Senin 10.00 WIB di `#minhub-control` (pola, kebingungan, saran). Bisa juga diminta
  kapan aja, misal *"ada learning baru dari clipper?"*.
- **Jeda humanis** 5–60 detik dengan status "typing..." sebelum membalas.
- **Pengumuman campaign baru** di `#pengumuman` (dicek tiap 3 menit): tag @everyone, teks variatif (nama, brand, rate,
  deadline, channel diskusi) + kartu campaign.
- **Konten top views** dari laporan client (sekali sehari per campaign mulai 19.00 WIB), dengan kartu preview buatan
  sendiri (thumbnail, caption, akun, platform, views, link). Campaign 🟢 dikirim otomatis (admin dikabari);
  campaign 🟡/🔴 dilewati. Kalau preview gambar gagal, Minhub coba konten berikutnya, lalu kirim tanpa gambar kalau
  gagal semua. Usulan yang nggak dijawab admin lewat `VIRAL_PENDING_MAX_HOURS` jam diputuskan sendiri. Admin juga bisa
  minta cek kapan aja.
- **Deteksi konten janggal**: rasio likes/views yang nggak wajar (curiga suntik views) nggak pernah di-share dan
  langsung dilaporkan ke `#minhub-control`. Batasnya per platform di `config.py` (`VIRAL_MIN_LIKE_RATIO`).
- **Tambah laporan lewat chat**: "laporan <campaign>: <link laporan>" di `#minhub-control` (disimpan di `reports.json`).
- **Pengingat harian 17.00 WIB** di `#diskusi-general`: tag @everyone, teks ditulis AI tiap hari + sisa budget tiap campaign.
  Aktif setelah admin react ✅ di contoh yang dikirim ke `#minhub-control`.
- **Nyambung sama permintaan sebelumnya**: kalau Minhub nanya balik, permintaan aslinya (channel, gambar, isi) tetap diinget
  dan dilanjutin begitu admin jawab (`open_requests.json`). Forward + komentar dibaca jadi satu perintah.
- **Draf tahan lama**: draf perintah admin disimpan di `drafts.json` selama `DRAFT_KEEP_HOURS` jam (tahan restart). Bisa
  di-acc kapan aja lewat ✅ atau chat (*"acc"*, *"kirim aja"*), oleh admin mana pun.
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

## Hosting 24/7 (Railway) & cara update
Bot jalan di Railway (paket Hobby), service-nya terhubung ke repo GitHub ini (branch `main`).
1. Ubah kode di PC → `git commit` → `git push`. Railway otomatis build & deploy ulang.
2. Cek `#minhub-control`: Minhub kirim "nyala lagi di **Railway** (versi `xxxxxxx`)". Versi itu harus sama dengan
   commit terakhir di GitHub.

Setting di Railway (sekali aja):
- **Variables**: `DISCORD_TOKEN`, `GEMINI_API_KEY`, dan `DATA_DIR=/data`. Token tidak ada di GitHub.
- **Volume** di-mount ke `/data`: tempat file state (riwayat konten, usulan yang nunggu acc, log). Tanpa Volume,
  data hilang tiap deploy. Pertama kali nyala, isi `seed_state/` disalin ke situ.
- `railway.json` mengatur perintah start (`python bot.py`) dan auto-restart.

Catatan:
- Minhub cuma boleh nyala di satu tempat. Server Wispbyte lama dimatikan (jangan di-Start lagi), dan jangan
  jalankan bot di PC bersamaan dengan Railway (balasan jadi dobel).
- Kalau koneksi ke Discord putus (misal IP diblokir), penjaga di `bot.py` nyoba login lagi sendiri.

## Izin bot (seminimal mungkin)
- Server-wide (role Minhub): View Channels, Send Messages, Embed Links, Attach Files, Read Message History,
  Add Reactions, Mention Everyone, Pin Messages.
- Khusus kategori "Diskusi Campaign" (permission overwrite untuk role Minhub): **Manage Channels** + **Manage Permissions**
  (buat bikin channel campaign baru dan ganti emoji status di namanya). Kategori "Campaign Closed" juga butuh izin yang sama
  (buat mindahin channel campaign yang selesai).
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
| `memory.json`, `memory_pending.json` | Catatan yang Minhub inget & usulan catatan yang nunggu acc |
| `events.jsonl`, `activity.jsonl` | Log event (buat rekap) & log aktivitas |

## Alat bantu
- `python cek_server.py` — cek bot sudah masuk server dan nama channel/role di `config.py` cocok.
- `python preview_welcome.py` — bikin `preview_welcome.png` untuk lihat kartu welcome.

## Catatan
- Pertama kali jalan, campaign yang sudah ada **tidak** diumumkan (biar nggak spam). Hanya campaign yang dibuat setelahnya.
- Role admin harus bisa di-mention (atau bot punya izin *Mention Everyone*) supaya tag admin berfungsi.
