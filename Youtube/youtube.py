# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | LISA-KOREA/YouTube-Video-Download-Bot

# [⚠️ Do not change this repo link ⚠️] :- https://github.com/LISA-KOREA/YouTube-Video-Download-Bot

import os
import glob
import uuid
import logging

import aiofiles
import aiohttp
import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from Youtube.config import Config
from Youtube.fix_thumb import fix_thumb
from Youtube.forcesub import handle_force_subscribe, humanbytes


YT_CACHE = {}


def get_ydl_options():
    """
    Common yt-dlp options.

    Empty/placeholder cookies.txt ko ignore karega.
    Sirf actual cookie entries hone par cookies use karega.
    """

    options = {
        "quiet": True,
        "js_runtimes": {
            "deno": {}
        },
    }

    cookie_file = "cookies.txt"

    if os.path.exists(cookie_file):
        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                has_real_cookies = any(
                    line.strip()
                    and not line.lstrip().startswith("#")
                    for line in f
                )

            if has_real_cookies:
                options["cookiefile"] = cookie_file
                logging.info("YouTube cookies enabled.")
            else:
                logging.info("cookies.txt is empty. Using YouTube without cookies.")

        except Exception as e:
            logging.warning(f"Could not read cookies.txt: {e}")

    return options


# ============================================================
# YouTube URL HANDLER
# ============================================================

@Client.on_message(
    filters.regex(
        r'^(http(s)?://)?(www\.)?(youtube\.com|youtu\.be)/.+'
    )
)
async def youtube_downloader(client, message):

    if Config.CHANNEL:
        fsub = await handle_force_subscribe(client, message)

        if fsub == 400:
            return

    url = message.text.strip()

    processing_msg = await message.reply_text(
        "🔍 **Fetching available formats...**"
    )

    ydl_opts = get_ydl_options()

    buttons = []

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

        formats = info.get("formats", [])
        duration = info.get("duration")
        title = info.get(
            "title",
            "YouTube Video"
        )

        vid_key = str(uuid.uuid4())[:8]

        YT_CACHE[vid_key] = url

        for f in formats:

            fmt_id = f.get("format_id")
            note = f.get("format_note") or f.get("format")
            ext = f.get("ext")

            size = (
                f.get("filesize")
                or f.get("filesize_approx")
            )

            size_text = (
                humanbytes(size)
                if size
                else "Unknown"
            )

            if not fmt_id:
                continue

            # Audio-only formats ko buttons me mat dikhana
            if (
                f.get("vcodec") == "none"
                or "audio" in str(note).lower()
            ):
                continue

            text = (
                f"{note or 'Unknown'} • "
                f"{size_text}"
            )

            callback_data = (
                f"ytdl|{vid_key}|"
                f"{fmt_id}|{ext}|video"
            )

            # Telegram callback data limit = 64 bytes
            if len(callback_data.encode()) <= 64:

                buttons.append([
                    InlineKeyboardButton(
                        text,
                        callback_data=callback_data
                    )
                ])

        # Audio button
        if duration:

            buttons.append([
                InlineKeyboardButton(
                    "🎵 Audio MP3",
                    callback_data=(
                        f"ytdl|{vid_key}|"
                        f"bestaudio|mp3|audio"
                    )
                )
            ])

        if not buttons:

            await processing_msg.edit_text(
                "❌ No downloadable formats found."
            )
            return

        await message.reply_text(
            f"**✅ Available formats for:**\n"
            f"`{title}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        await processing_msg.delete()

    except Exception as e:

        logging.exception(
            "Error fetching YouTube formats:"
        )

        await processing_msg.edit_text(
            f"❌ **Error:** `{e}`"
        )


# ============================================================
# DOWNLOAD HANDLER
# ============================================================

@Client.on_callback_query(
    filters.regex(r"^ytdl\|")
)
async def handle_download(client, cq):

    try:

        _, vid_key, fmt_id, ext, mode = (
            cq.data.split("|")
        )

        url = YT_CACHE.get(vid_key)

        if not url:

            await cq.message.edit_text(
                "⚠️ **Session expired.**\n"
                "Please send the YouTube link again."
            )
            return

        await cq.message.edit_text(
            "⬇️ **Downloading...**"
        )

        os.makedirs(
            "downloads",
            exist_ok=True
        )

        output = (
            f"downloads/{vid_key}.%(ext)s"
        )

        # Common yt-dlp options
        ydl_opts = get_ydl_options()

        if mode == "audio":

            ydl_opts.update({
                "format": "bestaudio/best",
                "outtmpl": output,

                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })

        else:

            ydl_opts.update({
                "format": (
                    f"{fmt_id}+bestaudio/best"
                ),
                "outtmpl": output,
                "merge_output_format": "mp4",
            })

        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            title = info.get(
                "title",
                "YouTube Video"
            )

            duration = info.get(
                "duration",
                0
            )

            width = info.get("width")
            height = info.get("height")

            thumb_url = info.get(
                "thumbnail"
            )

            filesize = (
                info.get("filesize")
                or info.get("filesize_approx")
            )

            file_size_text = (
                humanbytes(filesize)
                if filesize
                else "Unknown"
            )

        # ====================================================
        # Find actual downloaded file
        # ====================================================

        downloaded_files = glob.glob(
            f"downloads/{vid_key}.*"
        )

        downloaded_files = [
            f for f in downloaded_files
            if not f.endswith(".part")
        ]

        if not downloaded_files:

            raise FileNotFoundError(
                "Downloaded file was not found."
            )

        file_path = downloaded_files[0]

        # ====================================================
        # Thumbnail
        # ====================================================

        thumb_path = None

        if thumb_url:

            try:

                async with aiohttp.ClientSession() as session:

                    async with session.get(
                        thumb_url,
                        timeout=30
                    ) as response:

                        if response.status == 200:

                            thumb_path = (
                                f"downloads/"
                                f"{vid_key}_thumb.jpg"
                            )

                            async with aiofiles.open(
                                thumb_path,
                                "wb"
                            ) as f:

                                await f.write(
                                    await response.read()
                                )

            except Exception as e:

                logging.warning(
                    f"Thumbnail download failed: {e}"
                )

        # Fix thumbnail
        try:

            width, height, thumb_path = (
                await fix_thumb(thumb_path)
            )

        except Exception as e:

            logging.warning(
                f"Thumbnail processing failed: {e}"
            )

        await cq.message.edit_text(
            "📤 **Uploading...**"
        )

        # ====================================================
        # AUDIO
        # ====================================================

        if mode == "audio":

            await client.send_audio(

                chat_id=cq.message.chat.id,

                audio=file_path,

                caption=(
                    f"🎵 **{title}**\n"
                    f"📦 Size: `{file_size_text}`"
                ),

                duration=duration,

                thumb=(
                    thumb_path
                    if thumb_path
                    and os.path.exists(thumb_path)
                    else None
                ),
            )

        # ====================================================
        # VIDEO
        # ====================================================

        else:

            await client.send_video(

                chat_id=cq.message.chat.id,

                video=file_path,

                caption=(
                    f"🎬 **{title}**\n"
                    f"📦 Size: `{file_size_text}`"
                ),

                width=width,
                height=height,

                duration=duration,

                thumb=(
                    thumb_path
                    if thumb_path
                    and os.path.exists(thumb_path)
                    else None
                ),

                supports_streaming=True
            )

        await cq.message.edit_text(
            "✅ **Successfully Uploaded!**"
        )

        # ====================================================
        # CLEANUP
        # ====================================================

        try:

            if os.path.exists(file_path):
                os.remove(file_path)

            if (
                thumb_path
                and os.path.exists(thumb_path)
            ):
                os.remove(thumb_path)

        except Exception as e:

            logging.warning(
                f"Cleanup failed: {e}"
            )

    except Exception as e:

        logging.exception(
            "YouTube download error:"
        )

        try:

            await cq.message.edit_text(
                f"❌ **Error:** `{e}`"
            )

        except Exception:
            pass