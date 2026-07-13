# FILE: src/generator.py
# FINAL, CLEAN VERSION: Compatible with per-slide audio sync, dynamic slides, and GitHub Actions.

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
    """Converts text to speech using gTTS and ensures clean audio using WAV format."""
    print(f"🎤 Converting script to speech (Arabic)...")
    try:
        temp_mp3_path = str(output_path).replace('.mp3', '_temp.mp3')
        wav_path = str(output_path.with_suffix('.wav'))

        tts = gTTS(text=text, lang='ar', slow=False)
        tts.save(temp_mp3_path)

        audio = AudioSegment.from_mp3(temp_mp3_path)
        audio.export(wav_path, format="wav", codec="pcm_s16le")
        os.remove(temp_mp3_path)

        print(f"✅ Speech generated and converted to WAV successfully!")
        return Path(wav_path)

    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise


def generate_curriculum(previous_titles=None):
    """Generates the entire course curriculum using Gemini."""
    print("🤖 Generating a new curriculum for 'Unknown Files'...")
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        history = ""
        if previous_titles:
            formatted = "\n".join([f"{i+1}. {t}" for i, t in enumerate(previous_titles)])
            history = f"The following stories have already been created:\n{formatted}\n\nPlease continue from where this series left off.\n"

        prompt = f"""
        You are a mystery and true crime storyteller. Generate a list of 10 mysterious and shocking stories for a YouTube channel called 'Unknown Files'.
        {history}
        Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 10 lesson objects.
        Each lesson object must have these keys: "chapter", "part", "title", "status" (defaulted to "pending"), and "youtube_id" (defaulted to null).
        """
        # FIX: Using gemini-1.5-flash as the model name
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        curriculum = json.loads(json_string)
        print("✅ New curriculum generated successfully!")
        return curriculum
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Failed to generate curriculum. {e}")
        raise


def generate_lesson_content(lesson_title):
    """Generates the content for one mystery story."""
    print(f"🤖 Generating content for: '{lesson_title}'...")
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        prompt = f"""
        Create a mysterious story script in Arabic about '{lesson_title}'. 
        The tone should be shocking and cinematic.

        Generate a JSON response with three keys:
        1. "long_form_slides": A list of 7 to 8 slide objects. Each object needs a "title" and "content" key (both in Arabic).
        2. "short_form_highlight": A single, punchy summary for a Short (in Arabic).
        3. "hashtags": A string of 5-7 relevant hashtags (e.g., "#غموض #جرائم #قصص_واقعية").

        Return ONLY valid JSON.
        """
        # FIX: Using gemini-1.5-flash as the model name
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(json_string)
        print("✅ Lesson content generated successfully.")
        return content
    except Exception as e:
        print(f"❌ ERROR: Failed to generate lesson content: {e}")
        raise


def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    """Generates a single professional slide or a thumbnail."""
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None

    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    bg_image = get_pexels_image(title, video_type)

    if not bg_image:
        bg_image = Image.new('RGBA', (width, height), color=(12, 17, 29))
    bg_image = bg_image.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
    darken_layer = Image.new('RGBA', bg_image.size, (0, 0, 0, 150))
    final_bg = Image.alpha_composite(bg_image, darken_layer).convert("RGB")
    
    if is_thumbnail and video_type == 'long':
        w, h = final_bg.size
        if h > w:
            final_bg = final_bg.transpose(Image.ROTATE_270).resize((1920, 1080))
            
    draw = ImageDraw.Draw(final_bg)
    
    try:
        title_font = ImageFont.truetype(str(FONT_FILE), 80 if video_type == 'long' else 90)
    except IOError:
        title_font = FALLBACK_THUMBNAIL_FONT

    draw.text((width//10, height//2), title[:40], fill=(255, 255, 255))
    
    file_prefix = "thumbnail" if is_thumbnail else f"slide_{slide_number:02d}"
    path = output_dir / f"{file_prefix}.png"
    final_bg.save(path)
    return str(path)


def create_video(slide_paths, audio_paths, output_path, video_type):
    """Creates a final video from slides and audio clips."""
    print(f"🎬 Creating {video_type} video...")
    try:
        image_clips = []
        for img_path, audio_path in zip(slide_paths, audio_paths):
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration + 0.5
            img_clip = (
                ImageClip(img_path)
                .set_duration(duration)
                .set_audio(audio_clip)
                .fadein(0.5)
                .fadeout(0.5)
            )
            image_clips.append(img_clip)

        final_video = concatenate_videoclips(image_clips, method="compose")

        if BACKGROUND_MUSIC_PATH.exists():
            bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.05)
            if bg_music.duration < final_video.duration:
                bg_music = bg_music.fx(vfx.loop, duration=final_video.duration)
            else:
                bg_music = bg_music.subclip(0, final_video.duration)
            final_video = final_video.set_audio(CompositeAudioClip([final_video.audio.volumex(1.2), bg_music]))

        final_video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ Video created successfully!")

    except Exception as e:
        print(f"❌ ERROR during video creation: {e}")
        raise
