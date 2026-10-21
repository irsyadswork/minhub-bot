"""Lihat contoh kartu welcome tanpa nyalain bot: python preview_welcome.py -> preview_welcome.png"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

from welcome_card import make_welcome_card

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Avatar dummy: kotak ungu dengan huruf U
avatar = Image.new("RGB", (256, 256), (88, 101, 242))
ImageDraw.Draw(avatar).text((128, 128), "U", fill="white", anchor="mm", font=ImageFont.load_default(140))
buf = io.BytesIO()
avatar.save(buf, "PNG")

with open("preview_welcome.png", "wb") as f:
    f.write(make_welcome_card(buf.getvalue(), "ubet11.").read())
print("Tersimpan: preview_welcome.png")
