"""
Pengaturan bot Minhub. Ubah sesuai kebutuhan, lalu restart bot.
Channel & role dicari pakai ID dulu (aman walau di-rename). Nama cuma cadangan kalau ID-nya kosong/nggak ketemu.
Cara ambil ID: Discord > Settings > Advanced > Developer Mode ON, lalu klik kanan channel > Copy Channel ID.
"""

import os

# --- Lokasi file state (data runtime). Di Railway diisi lewat variabel DATA_DIR = folder Volume (misal /data),
# biar data nggak hilang tiap deploy. Kalau kosong, pakai folder bot ini. ---
DATA_DIR = os.environ.get("DATA_DIR") or os.path.dirname(os.path.abspath(__file__))

SERVER_NAME = "Clipper Hub Circle"
BOT_NAME = "Minhub"
CAMPAIGN_SITE = "https://campaign.clipperhub.site"

# --- Server yang boleh dipakai. Kalau bot dimasukkan ke server lain, otomatis keluar. ---
GUILD_ID = 1457619105803796604

# --- Channel (ID) ---
WELCOME_CHANNEL_ID = 1457619107666198579   # #welcome
GENERAL_CHANNEL_ID = 1562391135693832273   # #diskusi-general
CONTROL_CHANNEL_ID = 1562391137250181201   # #minhub-control
CAMPAIGN_CHANNEL_ID = 1458784634463846585  # #pengumuman
RULES_CHANNEL_ID = 1457960457251065877     # #rules
CAMPAIGN_CATEGORY_ID = 1562391140551102514 # kategori "Diskusi Campaign"
ADMIN_ROLE_ID = 1458782103377412293        # role Admin Komunitas
MENTOR_ROLE_ID = 1457969049207312521       # role Mentor (ikut di-tag & boleh setujui pengumuman deadline)

# --- Channel (nama cadangan) ---
WELCOME_CHANNEL = "welcome"            # tempat kartu welcome dikirim
GENERAL_CHANNEL = "diskusi"            # diskusi umum (dibuat otomatis kalau belum ada)
CONTROL_CHANNEL = "minhub-control"     # channel privat admin untuk ngasih perintah ke Minhub (dibuat otomatis)
REPLY_CHANNELS = ["campaign"]          # channel/forum lama yang namanya mengandung ini: bot balas kalau di-tag
RULES_CHANNEL = "rules"
CAMPAIGN_CHANNEL = "pengumuman"        # tempat pengumuman campaign baru

# --- Channel per campaign (dibuat & diatur otomatis oleh bot) ---
CAMPAIGN_CATEGORY = "Diskusi Campaign 🎬"
CAMPAIGN_CHANNEL_SEPARATOR = "・"       # nama channel: <status budget>・<slug campaign>

# --- Role admin yang di-tag untuk pertanyaan teknis & boleh ngasih perintah ---
ADMIN_ROLE = "Admin Komunitas"

# --- Welcome ---
# Teks welcome dipilih random dari texts.WELCOME
WELCOME_BACKGROUND = "assets/background.webp"
WELCOME_BG_FOCUS = 0.3                 # bagian background yang dipakai: 0 = atas, 1 = bawah
# Font dicoba berurutan (boleh pakai *). Montserrat ikut di folder assets, jadi tampilan sama di mana pun.
FONT_TITLE = ["assets/Montserrat.ttf", "C:/Windows/Fonts/seguibl.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONT_NAME = ["assets/Montserrat.ttf", "C:/Windows/Fonts/seguibl.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

# --- Balasan humanis ---
MIN_DELAY = 5                          # detik
MAX_DELAY = 60
AUTO_REPLY = True                      # di #diskusi & channel campaign: jawab pertanyaan walau nggak di-tag
AUTO_REPLY_COOLDOWN = 20               # detik minimal antar jawaban "nimbrung" di satu channel
HISTORY_MESSAGES = 10                  # berapa pesan terakhir yang dibaca biar paham konteks obrolan

# --- AI ---
# Dicoba berurutan: kalau model pertama lambat/overload, otomatis pindah ke berikutnya.
# Model pintar: jawab member yang nge-tag/bales Minhub, pertanyaan yang ada gambarnya, dan perintah admin.
GEMINI_MODELS_SMART = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.5-flash-lite", "gemini-flash-lite-latest"]
# Model ringan: nentuin perlu nimbrung atau nggak, nulis pengingat/pengumuman, ngeringkas jawaban admin jadi catatan.
GEMINI_MODELS_FAST = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-flash-latest"]
GEMINI_THINKING = "low"                # model pintar "mikir dulu" sebelum jawab: "low" / "high", kosongkan buat matiin
GEMINI_TIMEOUT = 15                    # detik per percobaan (model ringan)
GEMINI_TIMEOUT_SMART = 30              # detik per percobaan (model pintar, butuh waktu buat mikir)
MAX_IMAGES = 3                         # maks gambar per pesan yang ikut dibaca AI
MAX_IMAGE_MB = 5                       # gambar lebih gede dari ini nggak dibaca
MEMORY_MAX_NOTES = 100                 # maks catatan yang Minhub inget (yang paling lama dibuang duluan)
GEMINI_RETRIES = 1                     # kena 503/429/timeout: coba ulang sekian kali sebelum pindah model
GEMINI_RETRY_DELAY = 2                 # detik jeda sebelum coba ulang

# --- Keamanan & monitoring ---
RATE_LIMIT_PER_MINUTE = 5              # maks pertanyaan yang dijawab per member per menit (admin bebas)
RATE_LIMIT_PER_HOUR = 40
ALERT_COOLDOWN_MINUTES = 10            # alert yang sama ke channel kontrol paling sering sekali per sekian menit

# --- Share konten meledak dari laporan client (sekali sehari per campaign, tag @everyone) ---
# slug campaign di website -> kode laporan (bagian terakhir link laporan.clipperhub.site/laporan/<kode>)
REPORTS = {
    "menang-untuk-kalah-sound-of-panca": "chxsopan-3j5zdys01m",
    "jujutsu-kaisen-run-indonesia": "jujutsu-kaisen-fun-run-indonesia-v982l59ono",
    "film-siti-si-vampir-batch-4": "cpfssv4-1jamscke56",
    "internet-rakyat-sahabat-ira": "cpsahabatirach-pis58g8xbm",
    "ajaib-cuantalks": "ajaib-cuantalks-batch-5-bnw8d25be6",
    "film-pasukan-1000-janda": "cpfseribujanda3-g7losqt2s0",
    "semanis-drama-tropicana-slim": "istrikontrakxceodinginn-ccajrjyq3o",
    "todecella": "cpetodecellajakarta-n4yissjuhx",
    "shopee-11-11": "shopee-11-11-x-no-na-t92qyclpd4",
    "film-piye-to-kih": "film-piye-to-kih-1cfw6gredv",
    "fadil-jaidi-x-vitameal-podcast-raditya-dika": "fadil-jaidi-x-vitameal-pz22vib4ee",
    "film-the-doll-ghawiah": "the-doll-ghawiah-kntqc4n013",
}
# Laporan baru bisa ditambah lewat chat di #minhub-control ("laporan <campaign>: <link>"), disimpan di reports.json.

# Konten dianggap janggal (curiga suntik views) kalau likes/views di bawah batas ini, atau likes 0 padahal views
# udah >= VIRAL_SUSPICIOUS_MIN_VIEWS. Batas = kira-kira seperlima rasio normal tiap platform dari data laporan.
VIRAL_MIN_LIKE_RATIO = {"tiktok": 0.0008, "instagram": 0.0013, "youtube": 0.0022, "threads": 0.0003,
                        "facebook": 0.0008}
VIRAL_MIN_LIKE_RATIO_DEFAULT = 0.0008
VIRAL_SUSPICIOUS_MIN_VIEWS = 10_000
# Top views jam VIRAL_POST_HOUR dikirim otomatis (tanpa acc) cuma untuk campaign yang statusnya 🟢.
VIRAL_AUTO_SEND = True
# Nama panggilan campaign yang biasa dipakai member (slug -> alias). Kalau tetap ambigu, Minhub nanya balik.
CAMPAIGN_ALIASES = {
    "semanis-drama-tropicana-slim": ["dracin", "drama china", "semanis", "tropicana", "istri kontrak"],
    "film-siti-si-vampir-batch-4": ["siti", "ssv", "vampir"],
    "film-pasukan-1000-janda": ["1000 janda", "seribu janda", "pasukan janda"],
    "menang-untuk-kalah-sound-of-panca": ["panca", "menang untuk kalah"],
    "jujutsu-kaisen-run-indonesia": ["jjk", "jujutsu", "fun run"],
    "internet-rakyat-sahabat-ira": ["ira", "sahabat ira", "internet rakyat"],
    "ajaib-cuantalks": ["ajaib", "cuantalks"],
    "film-piye-to-kih": ["piye", "piye to kih"],
    "fadil-jaidi-x-vitameal-podcast-raditya-dika": ["fadil", "fadil jaidi", "vitameal", "raditya dika"],
    "film-the-doll-ghawiah": ["the doll", "doll", "ghawiah"],
}
VIRAL_POST_HOUR = 19                  # jam (WIB) mulai share tiap hari
VIRAL_MIN_VIEWS = 100_000              # minimal views normal
VIRAL_FALLBACK_MIN_VIEWS = 20_000      # minimal views kalau sudah lama nggak ada yang tembus 100rb
VIRAL_STUCK_DAYS = 3                   # "lama" = berapa hari nggak ada yang tembus 100rb

# --- Pengingat login Wispbyte (server gratis mati kalau 2 minggu nggak login) ---
LOGIN_REMINDER_DAYS = 12               # Minhub tag admin di channel kontrol tiap sekian hari
LOGIN_REMINDER_URL = "https://wispbyte.com/client"

# --- Pengumuman campaign baru ---
CAMPAIGN_CHECK_MINUTES = 3

# --- Status budget di nama channel campaign + update campaign ---
STATUS_CHECK_MINUTES = 30              # cek sisa budget & perubahan data campaign
BUDGET_YELLOW_PCT = 5                  # sisa > 0% s/d 5% = 🟡, di atas itu 🟢, 0% = 🔴
DEADLINE_REMINDER_HOUR = 9             # jam (WIB) kirim pengingat deadline H-1, dan tanya admin di hari H
                                       # (hari H: umumkan "hari terakhir" + @everyone cuma setelah admin/mentor react ✅)

# --- Pengingat harian di #diskusi-general ---
DAILY_REMINDER_HOUR = 17               # jam (WIB). Aktif setelah admin react ✅ di preview di #minhub-control

# --- Gambar cadangan untuk preview link (harus https, publik, idealnya 1200x630) ---
FALLBACK_IMAGES = ["https://campaign.clipperhub.site/opengraph-image"]
