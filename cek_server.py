"""Cek setup tanpa nyalain bot: login sebentar, tampilkan channel/role, dan apakah config.py cocok."""
import os

import discord
from dotenv import load_dotenv

import config
from bot import find_channel, find_role

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Login OK sebagai {client.user}")
    if not client.guilds:
        print("Bot belum ada di server mana pun. Invite dulu pakai link OAuth2.")
    for g in client.guilds:
        print(f"\n== Server: {g.name} ({g.member_count} member)")
        print("Channel teks:", ", ".join(c.name for c in g.text_channels))
        print("Role:", ", ".join(r.name for r in g.roles if not r.is_default()))
        print("\nCocok dengan config.py:")
        for label, name in [("WELCOME_CHANNEL", config.WELCOME_CHANNEL), ("BRIEF_CHANNEL", config.BRIEF_CHANNEL),
                            ("RULES_CHANNEL", config.RULES_CHANNEL), ("CAMPAIGN_CHANNEL", config.CAMPAIGN_CHANNEL),
                            *[("REPLY_CHANNELS", n) for n in config.REPLY_CHANNELS]]:
            ch = find_channel(g, name)
            ok = ch and ch.permissions_for(g.me).send_messages
            print(f"  {label:16} '{name}' -> {ch.name if ch else 'TIDAK KETEMU'}"
                  f"{'' if not ch else (' (bisa kirim)' if ok else ' (TIDAK bisa kirim pesan!)')}")
        for forum in g.forums:
            if any(want.lower() in forum.name.lower() for want in config.REPLY_CHANNELS):
                p = forum.permissions_for(g.me)
                ok = p.view_channel and p.send_messages_in_threads
                print(f"  {'FORUM':16} {forum.name}{' (bisa balas)' if ok else ' (TIDAK bisa balas!)'}")
        role = find_role(g, config.ADMIN_ROLE)
        print(f"  {'ADMIN_ROLE':16} '{config.ADMIN_ROLE}' -> {role.name if role else 'TIDAK KETEMU'}")
    await client.close()


client.run(os.environ["DISCORD_TOKEN"], log_handler=None)
