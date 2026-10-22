"""Template teks Minhub. Dipakai langsung (welcome) atau sebagai cadangan kalau Gemini gagal.
Aturan gaya: santai, nggak sok asik, emoji jarang (maks 1, cuma 😅 😂 🙏 👍 👀 📈)."""

# --- Welcome (#welcome), dipilih random tanpa API. {mention} = tag member, {server} = nama server ---
WELCOME = [
    "Halo {mention}, selamat datang di **{server}**! Kenalan dulu dong, biasanya nge-clip apa?",
    "Eh ada {mention}! Welcome di **{server}**. Kenalan dulu dong, udah lama nge-clip atau baru mau mulai?",
    "{mention} akhirnya mampir juga ke **{server}**. Yuk kenalan, asalnya dari mana nih?",
    "Selamat datang {mention}! Di **{server}** isinya clipper semua, jadi santai aja. Kenalin diri dulu yuk 👍",
    "Halo {mention}, makasih udah join **{server}**. Boleh kenalan? Biasanya upload di TikTok, Reels, atau Shorts?",
    "Welcome {mention}! Sebelum mulai, kenalan dulu yuk biar yang lain tau kamu siapa.",
    "Yeay, {mention} udah masuk **{server}**. Yuk kenalan, kamu clipper tipe apa, film, podcast, atau musik?",
    "Halo {mention}! Seneng kamu gabung di **{server}**. Kenalan dulu sini, siapa tau ketemu partner nge-clip.",
    "{mention} welcome! Di sini kita belajar bareng biar klipnya makin rame. Kenalan dulu yuk 🙏",
    "Selamat datang di **{server}**, {mention}. Jangan malu-malu, sapa yang lain dan kenalin diri kamu ya.",
    "Hai {mention}, welcome aboard di **{server}**! Kenalan dulu yuk, udah pernah ikut campaign clipping sebelumnya?",
    "Ada member baru nih, {mention}! Kenalan dulu yuk, nama panggilan sama akun clip kamu apa?",
    "Halo {mention}, selamat bergabung. Di **{server}** banyak yang bisa ditanya, mulai aja dari kenalan dulu.",
    "Welcome {mention}! Tarik kursi, santai dulu, terus kenalan sama yang lain ya.",
    "Akhirnya {mention} join juga wkwk. Selamat datang di **{server}**, kenalin diri dulu dong.",
    "Halo {mention}! Biar makin akrab, coba kenalan dulu: nama, domisili, sama niche clip kamu.",
    "{mention} selamat datang! Semoga betah di **{server}**. Yuk kenalan, biasanya nge-clip pakai apa?",
    "Halo halo {mention}, welcome di **{server}**. Sapa yang lain dulu yuk, kita kenalan.",
]

# --- Pengingat harian 17.00 WIB (cadangan kalau AI gagal). {budget} = ringkasan sisa budget ---
DAILY_REMINDER = [
    "Udah upload klip hari ini belum? Masih ada budget campaign yang bisa dikejar. Kalau ada kendala, tanya aja di sini.",
    "Sore check: klip hari ini udah naik belum? Budget campaign masih ada, jadi sayang kalau dilewatin. Bingung sesuatu? Tanya di sini ya.",
    "Jangan lupa upload hari ini ya. Cek sisa budget di bawah, terus kalau ada yang bikin bingung langsung tanya aja 👍",
    "Hari ini udah posting berapa klip? Budget campaign masih jalan, yuk dimanfaatin. Ada kendala apa pun, kabarin di sini.",
]

# --- Konten viral di channel campaign (cadangan kalau AI gagal) ---
VIRAL = [
    "Klip dari {user} di {platform} udah tembus **{views} views** buat campaign **{title}**. Coba pelajari hook-nya, siapa tau bisa jadi ide klip kamu berikutnya.",
    "Ada yang lagi rame nih: {user} dapet **{views} views** di {platform} untuk **{title}**. Lihat cara dia buka videonya 👀",
    "**{title}** lagi jalan bagus. Klip {user} di {platform} udah **{views} views**, bisa jadi referensi buat angle kamu.",
    "{user} bikin klip **{title}** yang udah ditonton **{views} kali** di {platform}. Amati, modifikasi, terus upload versi kamu sendiri.",
    "Satu lagi klip **{title}** yang nembus **{views} views** di {platform}, kali ini dari {user}. Cek preview-nya di bawah 📈",
]

# --- Pengumuman campaign baru di #pengumuman (cadangan kalau AI gagal) ---
ANNOUNCE = [
    "Ada campaign baru: **{title}** dari {brand}. Rate {rate}, deadline {deadline}. Detail dan diskusinya di {channel}.",
    "Campaign **{title}** ({brand}) udah buka. Bayarannya {rate} dan ditutup {deadline}. Ngobrolin brief-nya bisa di {channel}.",
    "Campaign baru dari {brand} nih: **{title}**. Rate {rate}, deadline {deadline}. Kalau ada yang mau ditanya, langsung ke {channel} ya.",
    "**{title}** dari {brand} resmi dibuka. {rate}, deadline {deadline}. Brief lengkap di bawah, diskusinya di {channel} 👀",
]

# --- Update data campaign di channel campaign ---
UPDATE_OPENER = [
    "Ada update buat campaign **{title}**:",
    "Info terbaru soal **{title}**, ada yang berubah nih:",
    "Heads up, detail **{title}** barusan diperbarui:",
    "Campaign **{title}** ada perubahan, cek dulu ya:",
]

DEADLINE_H1 = [
    "Deadline **{title}** besok ({deadline}). Kalau masih ada klip yang mau dikirim, kejar hari ini ya.",
    "Besok ({deadline}) campaign **{title}** udah tutup. Yang belum upload, masih ada waktu hari ini.",
]
DEADLINE_H = [
    "Hari ini hari terakhir **{title}** ({deadline}). Pastikan klip kamu udah ke-submit sebelum tutup ya 🙏",
    "Deadline **{title}** hari ini. Yang masih nyimpen draft, sekarang waktunya upload.",
]

# --- Status budget ---
BUDGET_RED = ("Budget campaign **{title}** udah habis, jadi klip baru nggak akan dibayar lagi. "
              "Tahan dulu upload-nya ya, nanti dikabarin kalau ada tambahan.")
