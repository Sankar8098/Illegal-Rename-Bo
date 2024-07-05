from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

from helper.utils import progress_for_pyrogram, convert, humanbytes
from helper.database import db

from asyncio import sleep
from PIL import Image
import os, time
import subprocess

# URL of the 5-second video to append
APPEND_VIDEO_URL = "https://s41-hzfi.freeconvert.com/task/6687f6c499fce3bf9be3a635/20230726_2243071.mp4"
APPEND_VIDEO_PATH = "append_video.mp4"

# Download the append video if it doesn't exist
if not os.path.exists(APPEND_VIDEO_PATH):
    import requests
    with requests.get(APPEND_VIDEO_URL, stream=True) as r:
        r.raise_for_status()
        with open(APPEND_VIDEO_PATH, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


@Client.on_message(filters.private & (filters.document | filters.audio | filters.video))
async def rename_start(client, message):
    file = getattr(message, message.media.value)
    filename = file.file_name
    if file.file_size > 2000 * 1024 * 1024:
        return await message.reply_text("Sᴏʀʀy Bʀᴏ Tʜɪꜱ Bᴏᴛ Iꜱ Dᴏᴇꜱɴ'ᴛ Sᴜᴩᴩᴏʀᴛ Uᴩʟᴏᴀᴅɪɴɢ Fɪʟᴇꜱ Bɪɢɢᴇʀ Tʜᴀɴ 2Gʙ. ᴄᴏɴᴛᴀᴄᴛ ʙᴏᴛ <a href='https://t.me/Illegal_Developer/10'>ᴅᴇᴠᴇʟᴏᴘᴇʀ</a>")

    try:
        await message.reply_text(
            text=f"**__Pʟᴇᴀꜱᴇ Eɴᴛᴇʀ Nᴇᴡ Fɪʟᴇɴᴀᴍᴇ...__**\n\n**Oʟᴅ Fɪʟᴇ Nᴀᴍᴇ** :- `{filename}`",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(True)
        )
        await sleep(30)
    except FloodWait as e:
        await sleep(e.value)
        await message.reply_text(
            text=f"**__Pʟᴇᴀꜱᴇ Eɴᴛᴇʀ Nᴇᴡ Fɪʟᴇɴᴀᴍᴇ...__**\n\n**Oʟᴅ Fɪʟᴇ Nᴀᴍᴇ** :- `{filename}`",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(True)
        )
    except:
        pass


@Client.on_message(filters.private & filters.reply)
async def refunc(client, message):
    reply_message = message.reply_to_message
    if (reply_message.reply_markup) and isinstance(reply_message.reply_markup, ForceReply):
        new_name = message.text
        await message.delete()
        msg = await client.get_messages(message.chat.id, reply_message.id)
        file = msg.reply_to_message
        media = getattr(file, file.media.value)
        if not "." in new_name:
            if "." in media.file_name:
                extn = media.file_name.rsplit('.', 1)[-1]
            else:
                extn = "mkv"
            new_name = new_name + "." + extn
        await reply_message.delete()

        button = [[InlineKeyboardButton("📁 Dᴏᴄᴜᴍᴇɴᴛ", callback_data="upload_document")]]
        if file.media in [MessageMediaType.VIDEO, MessageMediaType.DOCUMENT]:
            button.append([InlineKeyboardButton("🎥 Vɪᴅᴇᴏ", callback_data="upload_video")])
        elif file.media == MessageMediaType.AUDIO:
            button.append([InlineKeyboardButton("🎵 Aᴜᴅɪᴏ", callback_data="upload_audio")])
        await message.reply(
            text=f"**Sᴇʟᴇᴄᴛ Tʜᴇ Oᴜᴛᴩᴜᴛ Fɪʟᴇ Tyᴩᴇ**\n**• Fɪʟᴇ Nᴀᴍᴇ :-**`{new_name}`",
            reply_to_message_id=file.id,
            reply_markup=InlineKeyboardMarkup(button)
        )


@Client.on_callback_query(filters.regex("upload"))
async def doc(bot, update):
    new_name = update.message.text
    new_filename = new_name.split(":-")[1].strip()
    file_path = f"downloads/{new_filename}"
    file = update.message.reply_to_message

    ms = await update.message.edit("ɪʟʟᴇɢᴀʟ ᴅᴇᴠᴇʟᴏᴩᴇʀꜱ Tʀyɪɴɢ Tᴏ Dᴏᴡɴʟᴏᴀᴅɪɴɢ....")
    try:
        path = await bot.download_media(message=file, file_name=file_path, progress=progress_for_pyrogram, progress_args=("ɪʟʟᴇɢᴀʟ ᴅᴇᴠᴇʟᴏᴩᴇʀꜱ Dᴏᴡɴʟᴏᴀᴅ Sᴛᴀʀᴛᴇᴅ....", ms, time.time()))
    except Exception as e:
        return await ms.edit(e)

    # Merge the 5-second video
    merged_file_path = f"downloads/merged_{new_filename}"

    merge_command = [
        'ffmpeg', '-y', '-i', file_path, '-i', APPEND_VIDEO_PATH,
        '-filter_complex', '[0:v] [1:v] concat=n=2:v=1 [v]; [0:a:0?] [1:a:0?] concat=n=2:v=0:a=1 [a]',
        '-map', '[v]', '-map', '[a]', merged_file_path
    ]

    try:
        subprocess.run(merge_command, check=True)
    except subprocess.CalledProcessError as e:
        return await ms.edit(f"Error merging video: {e}")

    duration = 0
    try:
        metadata = extractMetadata(createParser(merged_file_path))
        if metadata.has("duration"):
            duration = metadata.get('duration').seconds
    except:
        pass
    ph_path = None
    user_id = int(update.message.chat.id)
    media = getattr(file, file.media.value)
    c_caption = await db.get_caption(update.message.chat.id)
    c_thumb = await db.get_thumbnail(update.message.chat.id)

    if c_caption:
        try:
            caption = c_caption.format(filename=new_filename, filesize=humanbytes(media.file_size), duration=convert(duration))
        except Exception as e:
            return await ms.edit(text=f"Yᴏᴜʀ Cᴀᴩᴛɪᴏɴ Eʀʀᴏʀ Exᴄᴇᴩᴛ Kᴇyᴡᴏʀᴅ Aʀɢᴜᴍᴇɴᴛ ●> ({e})")
    else:
        caption = f"**{new_filename}**"

    if media.thumbs or c_thumb:
        if c_thumb:
            ph_path = await bot.download_media(c_thumb)
        else:
            ph_path = await bot.download_media(media.thumbs[0].file_id)
        Image.open(ph_path).convert("RGB").save(ph_path)
        img = Image.open(ph_path)
        img.resize((320, 320))
        img.save(ph_path, "JPEG")

    await ms.edit("ɪʟʟᴇɢᴀʟ ᴅᴇᴠᴇʟᴏᴩᴇʀꜱ Tʀyɪɴɢ Tᴏ Uᴩʟᴏᴀᴅɪɴɢ....")
    type = update.data.split("_")[1]
    try:
        if type == "document":
            await bot.send_document(
                update.message.chat.id,
                document=merged_file_path,
                thumb=ph_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("Uᴩʟᴏᴅ Sᴛᴀʀᴛᴇᴅ....", ms, time.time()))
        elif type == "video":
            await bot.send_video(
                update.message.chat.id,
                video=merged_file_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("Uᴩʟᴏᴅ Sᴛᴀʀᴛᴇᴅ....", ms, time.time()))
        elif type == "audio":
            await bot.send_audio(
                update.message.chat.id,
                audio=merged_file_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("Uᴩʟᴏᴅ Sᴛᴀʀᴛᴇᴅ....", ms, time.time()))
    except Exception as e:
        os.remove(file_path)
        os.remove(merged_file_path)
        if ph_path:
            os.remove(ph_path)
        return await ms.edit(f"Error: {e}")

    await ms.delete()
    os.remove(file_path)
    os.remove(merged_file_path)
    if ph_path:
        os.remove(ph_path)
