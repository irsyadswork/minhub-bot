"""Preview link yang nggak boleh rusak.

- og_info(url): baca meta tag og:* sebuah halaman.
- valid_image(url): gambar beneran bisa diambil (https, 200, image/*, bisa dibuka Pillow, bukan placeholder kecil).
- prepare(text): sebelum kirim teks berisi link, cek preview-nya. Kalau og:image rusak, link dibungkus <...>
  (preview bawaan Discord dimatikan) dan diganti embed buatan sendiri dengan gambar cadangan yang valid.
- content_preview(url): data preview konten viral (thumbnail, caption, akun) dengan urutan
  oEmbed -> meta og:image -> screenshot. Thumbnail diunduh & dilampirkan sebagai file supaya nggak kedaluwarsa.
"""
import asyncio
import html
import io
import json
import logging
import re
import time
from urllib.parse import quote, urlparse

import aiohttp
import discord
from PIL import Image

import config

log = logging.getLogger("minhub")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
URL_RE = re.compile(r"(?<![<(])https?://[^\s<>()]+[^\s<>().,!?;:'\"]")
_cache: dict = {}
CACHE_SECONDS = 1800


def _cached(key):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return True, hit[1]
    return False, None


def _remember(key, value):
    _cache[key] = (time.monotonic(), value)
    return value


# Instagram/Threads cuma ngasih meta og:* ke crawler preview (yang dipakai Facebook/Discord), bukan ke browser biasa.
CRAWLER_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


async def _get(session, url, limit=2_000_000, ua=UA):
    async with session.get(url, headers={"User-Agent": ua, "Accept-Language": "id,en;q=0.8"},
                           timeout=aiohttp.ClientTimeout(total=15), allow_redirects=True) as r:
        chunks, size = [], 0
        async for chunk in r.content.iter_chunked(65536):
            chunks.append(chunk)
            size += len(chunk)
            if size >= limit:
                break
        return r.status, r.headers.get("Content-Type", ""), b"".join(chunks), str(r.url)


def _meta(page: str, *names) -> str | None:
    for name in names:
        for pat in (rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]*content=["\']([^"\']*)["\']',
                    rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']{re.escape(name)}["\']'):
            m = re.search(pat, page, re.IGNORECASE)
            if m and m.group(1).strip():
                return html.unescape(m.group(1).strip())
    return None


async def og_info(url: str) -> dict:
    ok, val = _cached(("og", url))
    if ok:
        return val
    info = {}
    for ua in (UA, CRAWLER_UA):
        info = await _og_once(url, ua)
        if info.get("image"):
            break
    return _remember(("og", url), info)


async def _og_once(url: str, ua: str) -> dict:
    info = {}
    try:
        async with aiohttp.ClientSession() as s:
            status, ctype, body, final = await _get(s, url, 600_000, ua)
        if status == 200 and "html" in ctype:
            page = body.decode("utf-8", "ignore")
            info = {
                "title": _meta(page, "og:title", "twitter:title"),
                "description": _meta(page, "og:description", "description", "twitter:description"),
                "image": _meta(page, "og:image", "og:image:url", "twitter:image"),
            }
            # TikTok nggak selalu pasang og:image, tapi data halamannya nyimpen cover & caption video
            if not info["image"]:
                m = re.search(r'"(?:originCover|cover)":"(https:[^"]+)"', page)
                if m:
                    info["image"] = json.loads(f'"{m.group(1)}"')
            if not info["description"]:
                m = re.search(r'"desc":"((?:[^"\\]|\\.){1,500})"', page)
                if m:
                    info["description"] = json.loads(f'"{m.group(1)}"')
    except Exception as e:
        log.info("og_info %s gagal: %s", url, e)
    return _remember(("og", url), info)


async def fetch_image(url: str) -> bytes | None:
    """Unduh gambar & pastikan valid. Balikin bytes JPEG/PNG siap kirim, atau None."""
    if not url or not url.startswith("https://"):
        return None
    host = urlparse(url).hostname or ""
    if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
        return None
    try:
        async with aiohttp.ClientSession() as s:
            status, ctype, body, _ = await _get(s, url, 8_000_000)
        if status != 200 or not ctype.startswith("image/"):
            return None
        img = Image.open(io.BytesIO(body))
        img.load()
        if img.width < 200 or img.height < 150:  # ikon/placeholder kecil
            return None
        if img.format in ("JPEG", "PNG"):
            return body
        out = io.BytesIO()
        img.convert("RGB").save(out, "JPEG", quality=88)
        return out.getvalue()
    except Exception as e:
        log.info("Gambar %s nggak valid: %s", url[:120], e)
        return None


async def valid_image(url: str) -> bool:
    ok, val = _cached(("img", url))
    if ok:
        return val
    return _remember(("img", url), (await fetch_image(url)) is not None)


async def clean_embed(embed: discord.Embed) -> discord.Embed:
    """Buang gambar/thumbnail embed yang nggak valid, biar nggak pernah tampil gambar rusak."""
    if embed.image and embed.image.url and not embed.image.url.startswith("attachment://"):
        if not await valid_image(embed.image.url):
            fallback = await fallback_image()
            embed.set_image(url=fallback) if fallback else embed.remove_image()
    if embed.thumbnail and embed.thumbnail.url and not embed.thumbnail.url.startswith("attachment://"):
        if not await valid_image(embed.thumbnail.url):
            embed.remove_thumbnail()
    return embed


async def fallback_image() -> str | None:
    for url in config.FALLBACK_IMAGES:
        if await valid_image(url):
            return url
    return None


async def _site_image(url: str) -> str | None:
    """Gambar yang pas untuk link website campaign: poster campaign kalau link-nya halaman campaign."""
    m = re.search(r"/campaigns/([\w-]+)", url)
    if m and _poster_lookup:
        poster = _poster_lookup(m.group(1))
        if poster and await valid_image(poster):
            return poster
    return await fallback_image()


_poster_lookup = None  # diisi bot: slug -> url poster


def set_poster_lookup(fn):
    global _poster_lookup
    _poster_lookup = fn


async def prepare(text: str, max_embeds: int = 2) -> tuple[str, list[discord.Embed]]:
    """Validasi preview semua link di teks. Link yang preview-nya rusak dibungkus <...> + embed cadangan."""
    embeds = []
    for url in dict.fromkeys(URL_RE.findall(text or "")):
        info = await og_info(url)
        image = info.get("image")
        if image and await valid_image(image):
            continue  # preview bawaan Discord aman
        text = re.sub(rf"(?<![<(]){re.escape(url)}(?!>)", f"<{url}>", text)
        if len(embeds) >= max_embeds:
            continue
        host = urlparse(url).hostname or url
        site = config.CAMPAIGN_SITE.split("//", 1)[-1]
        title = info.get("title") or ("Clipper Hub Campaigns" if site in host else host)
        embed = discord.Embed(title=title[:256], url=url, description=(info.get("description") or "")[:300] or None,
                              color=0x488CFF)
        img = await _site_image(url) if site in host else None
        if img:
            embed.set_image(url=img)
        embed.set_footer(text=config.SERVER_NAME)
        embeds.append(embed)
    return text, embeds


# ---------- preview konten viral ----------

OEMBED = {
    "tiktok.com": "https://www.tiktok.com/oembed?url={u}",
    "youtube.com": "https://www.youtube.com/oembed?format=json&url={u}",
    "youtu.be": "https://www.youtube.com/oembed?format=json&url={u}",
    "threads.net": "https://www.threads.net/oembed/?url={u}",
    "threads.com": "https://www.threads.net/oembed/?url={u}",
}


async def _oembed(url: str) -> dict | None:
    host = (urlparse(url).hostname or "").removeprefix("www.").removeprefix("m.").removeprefix("vm.")
    tpl = next((v for k, v in OEMBED.items() if host == k or host.endswith("." + k)), None)
    if not tpl:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(tpl.format(u=quote(url, safe="")), headers={"User-Agent": UA},
                             timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return None
                data = await r.json(content_type=None)
        return {"image": data.get("thumbnail_url"), "caption": data.get("title"),
                "author": data.get("author_unique_id") or data.get("author_name")}
    except Exception as e:
        log.info("oEmbed %s gagal: %s", url, e)
        return None


async def _screenshot(url: str) -> bytes | None:
    shot = f"https://s0.wp.com/mshots/v1/{quote(url, safe='')}?w=1200&h=900"
    for _ in range(3):  # layanan ini kirim gambar "loading" dulu, jadi dicoba beberapa kali
        data = await fetch_image(shot)
        if data:
            img = Image.open(io.BytesIO(data))
            if img.format != "GIF" and len(data) > 15_000:
                return data
        await asyncio.sleep(15)
    return None


async def content_preview(url: str) -> dict | None:
    """{image_bytes, caption, author, source} atau None kalau semua cara gagal."""
    caption = None
    m = re.search(r"/@([\w.]+)", url)
    author = m.group(1) if m else None
    oe = await _oembed(url)
    if oe:
        caption, author = oe.get("caption"), oe.get("author") or author
        data = await fetch_image(oe.get("image"))
        if data:
            return {"image": data, "caption": caption, "author": author, "source": "oembed"}
    og = await og_info(url)
    caption = caption or og.get("description") or og.get("title")
    data = await fetch_image(og.get("image"))
    if data:
        return {"image": data, "caption": caption, "author": author, "source": "og:image"}
    # Screenshot TikTok/Instagram/Threads selalu ketutup popup login, jadi bukan preview yang layak
    walled = any(h in (urlparse(url).hostname or "") for h in ("tiktok.com", "instagram.com", "threads.net",
                                                                 "threads.com"))
    data = None if walled else await _screenshot(url)
    if data:
        return {"image": data, "caption": caption, "author": author, "source": "screenshot"}
    return None
