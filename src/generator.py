import os
import json
import requests
from io import BytesIO
from google import genai
from gtts import gTTS
from moviepy.editor import AudioFileClip, ImageClip, CompositeAudioClip, concatenate_videoclips, vfx
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from pydub import AudioSegment

# --- Configuration ---
ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music/bg_music.mp3"
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "Unknown Files"

# GitHub Actions compatibility for ImageMagick
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def get_pexels_image(query, video_type):
    """Searches for a relevant image on Pexels and returns the image object."""
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        print("⚠️ PEXELS_API_KEY not found. Using solid color background.")
        return None

    orientation = 'landscape' if video_type == 'long' else 'portrait'
    try:
        headers = {"Authorization": pexels_api_key}
        params = {"query": f"mysterious {query}", "per_page": 1, "orientation": orientation}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get('photos'):
            image_url = data['photos'][0]['src']['large2x']
            image_response = requests.get(image_url, timeout=15)
            image_response.raise_for_status()
            return Image.open(BytesIO(image_response.content)).convert("RGBA")
    except Exception as e:
        print(f"❌ Error fetching Pexels image: {e}")
    return None

def text_to_speech(text, output_path):
    """Converts text to speech using gTTS (Arabic)."""
    print(f"🎤 Converting script to speech (Arabic)...")
    try:
        temp_mp3_path = str(output_path).replace('.mp3', '_temp.mp3')
        wav_path = str(output_path.with_suffix('.wav'))
        tts = gTTS(text=text, lang='ar', slow=False)
        tts.save(temp_mp3_path)
        audio = AudioSegment.from_mp3(temp_mp3_path)
        audio.export(wav_path, format="wav", codec="pcm_s16le")
        os.remove(temp_mp3_path)
        return Path(wav_path)
    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise

def generate_curriculum(previous_titles=None):
    """Generates the entire course curriculum using Gemini."""
    print("🤖 Generating curriculum for 'Unknown Files'...")
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        prompt = """
        Generate a JSON with a list of 10 mysterious stories for 'Unknown Files' channel. 
        Format: {"lessons": [{"chapter": 1, "part": 1, "title": "Story Title", "status": "pending", "youtube_id": null}]}.
        Return ONLY valid JSON.
        """
        # استخدام الموديل الصحيح gemini-1.5-flash
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_string)
    except Exception as e:
        print(f"❌ Curriculum Error: {e}")
        raise

def generate_lesson_content(lesson_title):
    """Generates the content for one mystery story."""
    print(f"🤖 Generating content for: '{lesson_title}'...")
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        prompt = f"""
        Write a mysterious story about '{lesson_title}' in Arabic. 
        Generate a JSON response with:
        1. "long_form_slides": A list of 7 slide objects (title and content in Arabic).
        2. "short_form_highlight": A punchy 1-2 sentence summary in Arabic.
        3. "hashtags": A string of hashtags.
        Return ONLY valid JSON.
        """
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_string)
    except Exception as e:
        print(f"❌ Lesson Content Error: {e}")
        raise

def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    """Generates slides or thumbnails."""
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    bg_image = get_pexels_image(title, video_type)
    if not bg_image:
        bg_image = Image.new('RGBA', (width, height), color=(15, 15, 15))
    bg_image = bg_image.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
    final_bg = Image.alpha_composite(bg_image, Image.new('RGBA', bg_image.size, (0, 0, 0, 180))).convert("RGB")
    draw = ImageDraw.Draw(final_bg)
    draw.text((width//10, height//2), title[:40], fill=(255, 255, 255))
    path = output_dir / f"{'thumbnail' if is_thumbnail else f'slide_{slide_number:02d}'}.png"
    final_bg.save(path)
    return str(path)

def create_video(slide_paths, audio_paths, output_path, video_type):
    """Creates final video (Full implementation)."""
    print(f"🎬 Creating {video_type} video...")
    try:
        image_clips = []
        for img_path, audio_path in zip(slide_paths, audio_paths):
            audio_clip = AudioFileClip(str(audio_path))
            img_clip = ImageClip(img_path).set_duration(audio_clip.duration + 0.5).set_audio(audio_clip).fadein(0.5).fadeout(0.5)
            image_clips.append(img_clip)
        final_video = concatenate_videoclips(image_clips, method="compose")
        if BACKGROUND_MUSIC_PATH.exists():
            bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.05)
            bg_music = bg_music.fx(vfx.loop, duration=final_video.duration)
            final_video = final_video.set_audio(CompositeAudioClip([final_video.audio.volumex(1.2), bg_music]))
        final_video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ Video created: {output_path}")
    except Exception as e:
        print(f"❌ Video Creation Error: {e}")
        raise
