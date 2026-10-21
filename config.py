"""
Pengaturan bot Minhub. Ubah sesuai kebutuhan, lalu restart bot.
Nama channel/role boleh sebagian saja (misal "welcome" cocok dengan "👋・welcome").
"""

SERVER_NAME = "Clipper Hub Circle"
BOT_NAME = "Minhub"
CAMPAIGN_SITE = "https://campaign.clipperhub.site"

# --- Channel ---
WELCOME_CHANNEL = "welcome-and-rules"  # tempat kartu welcome dikirim
GENERAL_CHANNEL = "diskusi"            # diskusi umum (dibuat otomatis kalau belum ada)
CONTROL_CHANNEL = "minhub-control"     # channel privat admin untuk ngasih perintah ke Minhub (dibuat otomatis)
REPLY_CHANNELS = ["campaign"]          # channel/forum lama yang namanya mengandung ini: bot balas kalau di-tag
RULES_CHANNEL = "rules"
CAMPAIGN_CHANNEL = "pengumuman"        # tempat pengumuman campaign baru

# --- Channel per campaign (dibuat & diatur otomatis oleh bot) ---
CAMPAIGN_CATEGORY = "Diskusi Campaign 🎬"
CAMPAIGN_CHANNEL_PREFIX = "🎬・"

# --- Role admin yang di-tag untuk pertanyaan teknis & boleh ngasih perintah ---
ADMIN_ROLE = "Admin Komunitas"

# --- Welcome ---
WELCOME_TEXT = "Yooo {mention}, welcome di **{server}**! 🎬 Jangan lupa kenalan dulu ya~"
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
GEMINI_MODELS = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]
GEMINI_TIMEOUT = 15                    # detik per percobaan

# --- Share konten meledak dari laporan client (sekali sehari per campaign, tag @everyone) ---
# slug campaign di website -> kode laporan (bagian terakhir link laporan.clipperhub.site/laporan/<kode>)
REPORTS = {
    "menang-untuk-kalah-sound-of-panca": "chxsopan-3j5zdys01m",
    "jujutsu-kaisen-run-indonesia": "jujutsu-kaisen-fun-run-indonesia-v982l59ono",
    "film-siti-si-vampir-batch-4": "cpfssv4-1jamscke56",
    "internet-rakyat-sahabat-ira": "cpsahabatirach-pis58g8xbm",
    "ajaib-cuantalks": "ajaib-cuantalks-batch-5-bnw8d25be6",
    "film-pasukan-1000-janda": "cpfseribujanda3-g7losqt2s0",
}
VIRAL_POST_HOUR = 19                   # jam (WIB) mulai share tiap hari
VIRAL_MIN_VIEWS = 100_000              # minimal views normal
VIRAL_FALLBACK_MIN_VIEWS = 20_000      # minimal views kalau sudah lama nggak ada yang tembus 100rb
VIRAL_STUCK_DAYS = 3                   # "lama" = berapa hari nggak ada yang tembus 100rb

# --- Pengumuman campaign baru ---
CAMPAIGN_CHECK_MINUTES = 3
CAMPAIGN_TEXT = "🚨 **Campaign baru drop, guys!** Gas join sebelum slotnya penuh 👇"
