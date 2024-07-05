from config import Config
from helper.database import db
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
from moviepy.editor import VideoFileClip, concatenate_videoclips
import os, sys, time, asyncio, logging, datetime
from PIL import Image

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MERGE_VIDEO_PATH = "downloads/ending_video.mp4"  # Path to the video that should be merged

@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    total_users = await db.total_users_count()
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))    
    start_t = time.time()
    st = await message.reply('**Accessing the details.....**')    
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(text=f"**--Bot Status--** \n\n**⌚️ Bot Uptime:** {uptime} \n**🐌 Current Ping:** `{time_taken_s:.3f} ms` \n**👭 Total Users:** `{total_users}`")


@Client.on_message(filters.private & filters.command("restart") & filters.user(Config.ADMIN))
async def restart_bot(b, m):
    await m.reply_text("🔄 Restarting.....")
    os.execl(sys.executable, sys.executable, *sys.argv)


@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    await bot.send_message(Config.LOG_CHANNEL, f"{m.from_user.mention} or {m.from_user.id} has started the broadcast...")
    all_users = await db.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("Broadcast started...!")
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await db.total_users_count()
    async for user in all_users:
        sts = await send_msg(user['_id'], broadcast_msg)
        if sts == 200:
            success += 1
        else:
            failed += 1
        if sts == 400:
            await db.delete_user(user['_id'])
        done += 1
        if not done % 20:
            await sts_msg.edit(f"Broadcast in progress: \nTotal Users: {total_users} \nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}")
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(f"Broadcast completed: \nCompleted in `{completed_in}`.\n\nTotal Users: {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}")
           
async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id} : Deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id} : Blocked the bot")
        return 400
    except PeerIdInvalid:
        logger.info(f"{user_id} : User ID Invalid")
        return 400
    except Exception as e:
        logger.error(f"{user_id} : {e}")
        return 500

async def merge_videos(original_video_path, merge_video_path, output_path):
    try:
        original_clip = VideoFileClip(original_video_path)
        merge_clip = VideoFileClip(merge_video_path)
        final_clip = concatenate_videoclips([original_clip, merge_clip])
        final_clip.write_videofile(output_path)
        original_clip.close()
        merge_clip.close()
        final_clip.close()
        return True
    except Exception as e:
        logger.error(f"Error merging videos: {e}")
        return False

@Client.on_callback_query(filters.regex("upload"))
async def doc(bot, update):    
    new_name = update.message.text
    new_filename = new_name.split(":-")[1].strip()
    file_path = f"downloads/{new_filename}"
    file = update.message.reply_to_message

    ms = await update.message.edit("Trying to download....")    
    try:
        path = await bot.download_media(message=file, file_name=file_path, progress=progress_for_pyrogram, progress_args=("Download started....", ms, time.time()))                    
    except Exception as e:
        return await ms.edit(e)
         
    duration = 0
    try:
        metadata = extractMetadata(createParser(file_path))
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
            return await ms.edit(text=f"Your caption error except keyword argument ●> ({e})")             
    else:
        caption = f"**{new_filename}**"
 
    if (media.thumbs or c_thumb):
        if c_thumb:
            ph_path = await bot.download_media(c_thumb) 
        else:
            ph_path = await bot.download_media(media.thumbs[0].file_id)
        Image.open(ph_path).convert("RGB").save(ph_path)
        img = Image.open(ph_path)
        img.resize((320, 320))
        img.save(ph_path, "JPEG")

    await ms.edit("Trying to upload....")
    type = update.data.split("_")[1]
    
    # Merge video if the type is video
    if type == "video":
        output_path = f"downloads/merged_{new_filename}"
        if await merge_videos(file_path, MERGE_VIDEO_PATH, output_path):
            file_path = output_path

    try:
        if type == "document":
            await bot.send_document(
                update.message.chat.id,
                document=file_path,
                thumb=ph_path, 
                caption=caption, 
                progress=progress_for_pyrogram,
                progress_args=("Upload started....", ms, time.time()))
        elif type == "video": 
            await bot.send_video(
                update.message.chat.id,
                video=file_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("Upload started....", ms, time.time()))
        elif type == "audio": 
            await bot.send_audio(
                update.message.chat.id,
                audio=file_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("Upload started....", ms, time.time()))
    except Exception as e:          
        os.remove(file_path)
        if ph_path:
            os.remove(ph_path)
        return await ms.edit(f" Error {e}")
 
    await ms.delete() 
    os.remove(file_path) 
    if ph_path: os.remove(ph_path) 

# Command to set the merge video
@Client.on_message(filters.command("setmergevideo") & filters.user(Config.ADMIN) & filters.reply)
async def set_merge_video(bot, message):
    if not message.reply_to_message.video:
        return await message.reply_text("Please reply to a video to set it as the ending video.")
    
    ms = await message.reply_text("Downloading video...")
    video_path = f"downloads/ending_video.mp4"
    
    try:
        await bot.download_media(message.reply_to_message, file_name=video_path)
        await ms.edit("Video set successfully as the ending video!")
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        await ms.edit(f"Failed to set the video: {e}")
