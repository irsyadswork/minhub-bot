"""
Pengaturan bot Minhub. Ubah sesuai kebutuhan, lalu restart bot.
Nama channel/role boleh sebagian saja (misal "welcome" cocok dengan "👋・welcome").
"""

SERVER_NAME = "Clipper Hub Circle"
BOT_NAME = "Minhub"
CAMPAIGN_SITE = "https://campaign.clipperhub.site"

# --- Channel ---
WELCOME_CHANNEL = "welcome-and-rules"  # tempat kartu welcome dikirim
REPLY_CHANNELS = ["campaign", "diskusi"]  # bot cuma balas tag di channel/forum yang namanya mengandung ini ([] = semua)
BRIEF_CHANNEL = ""                     # dirujuk kalau pertanyaannya teknis (kosongkan "" kalau belum ada)
RULES_CHANNEL = "rules"
CAMPAIGN_CHANNEL = "pengumuman"        # tempat pengumuman campaign baru

# --- Role admin yang di-tag untuk pertanyaan teknis ---
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

# --- AI ---
GEMINI_MODEL = "gemini-flash-latest"

# --- Pengumuman campaign baru ---
CAMPAIGN_CHECK_MINUTES = 3
CAMPAIGN_TEXT = "🚨 **Campaign baru drop, guys!** Gas join sebelum slotnya penuh 👇"
