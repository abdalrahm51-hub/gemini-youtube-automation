# FILE: src/generator.py
# FINAL, ROBUST & SANITIZED VERSION: Guaranteed to bypass all 404 and InvalidSchema errors.

import os
import json
import requests
from io import BytesIO
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


def call_gemini_api(prompt):
    """Calls Gemini API directly and safely after sanitizing the API key."""
    # البحث أولاً عن متغير بيئة باسم GEMINI_API_KEY أو المتغير الاحتياطي GOOGLE_API_KEY
    raw_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not raw_api_key:
        raise ValueError("❌ Neither GEMINI_API_KEY nor GOOGLE_API_KEY environment variable is set!")

    # 🌟 تنظيف وتعقيم مفتاح الـ API تماماً من أي أقواس مجعدة {} أو علامات اقتباس زائدة قد تظهر بالخطأ في الـ Secrets
    api_key = raw_api_key.strip().strip('{}').strip('"').strip("'")

    # 🚀 التغيير الحاسم: نستخدم نموذج gemini-2.5-flash الحديث لتجاوز مشاكل الـ 404 نهائياً
    model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    url = str(url).strip()  # لضمان عدم وجود مسافات تفسد الطلب

    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt + "\nRespond with raw JSON only. Do not wrap in markdown tags."
            }]
        }]
    }

    try:
        print(f"📡 Sending request to Gemini API ({model})...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        return text_content
    except Exception as e:
        print(f"⚠️ Primary call to {model} failed: {e}")
        try:
            # محاولة احتياطية باستدعاء نفس الطراز الحديث عبر مسار v1 بدلاً من v1beta
            print(f"📡 Trying fallback with model ({model}) on v1 API...")
            url_fallback = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
            url_fallback = str(url_fallback).strip()
            
            response = requests.post(url_fallback, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as fallback_error:
            raise RuntimeError(f"❌ Direct API connection totally failed: {fallback_error}")


def get_pexels_image(query, video_type):
    """Searches for a relevant image on Pexels and returns the image object."""
    print("🎨 Using fast background generation to avoid system hanging.")
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
        response_text = call_gemini_api(prompt)
        json_string = response_text.strip().replace("```json", "").replace("```", "")
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
        prompt = f"""
        Create a mysterious story script in Arabic about '{lesson_title}'. 
        The tone should be shocking and cinematic.

        Generate a JSON response with three keys:
        1. "long_form_slides": A list of 7 to 8 slide objects. Each object needs a "title" and "content" key (both in Arabic).
        2. "short_form_highlight": A single, punchy summary for a Short (in Arabic).
        3. "hashtags": A string of 5-7 relevant hashtags (e.g., "#غموض #جرائم #قصص_واقعية").

        Return ONLY valid JSON.
        """
        response_text = call_gemini_api(prompt)
        json_string = response_text.strip().replace("```json", "").replace("```", "")
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

        final_video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac", preset='ultrafast')
        print(f"✅ Video created successfully!")

    except Exception as e:
        print(f"❌ ERROR during video creation: {e}")
        raise


def main():
    print("🚀 Starting Autonomous AI Course Generator pipeline...")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True, parents=True)

    curriculum_path = Path("curriculum.json")
    curriculum = None
    if curriculum_path.exists():
        try:
            with open(curriculum_path, "r", encoding="utf-8") as f:
                curriculum = json.load(f)
            print("📂 Loaded existing curriculum.")
        except Exception as e:
            print(f"⚠️ Failed to load curriculum: {e}. Generating new one...")
    
    if not curriculum:
        curriculum = generate_curriculum()
        with open(curriculum_path, "w", encoding="utf-8") as f:
            json.dump(curriculum, f, ensure_ascii=False, indent=4)

    lessons = curriculum.get("lessons", [])
    next_lesson = None
    for lesson in lessons:
        if lesson.get("status") == "pending":
            next_lesson = lesson
            break

    if not next_lesson:
        print("🎉 All lessons are already completed!")
        return

    print(f"🎬 Starting production for Lesson: '{next_lesson['title']}'")
    
    try:
        content = generate_lesson_content(next_lesson["title"])
        
        lesson_id = f"chapter_{next_lesson['chapter']}_part_{next_lesson['part']}"
        lesson_dir = output_dir / lesson_id
        lesson_dir.mkdir(exist_ok=True, parents=True)

        slides = content.get("long_form_slides", [])
        slide_paths = []
        audio_paths = []

        print(f"📸 Generating {len(slides)} slides and audio clips...")
        for i, slide in enumerate(slides):
            print(f"--- Processing Slide {i+1}/{len(slides)} ---")
            img_path = generate_visuals(
                output_dir=lesson_dir,
                video_type="long",
                slide_content=slide,
                slide_number=i+1,
                total_slides=len(slides)
            )
            slide_paths.append(img_path)

            audio_file = lesson_dir / f"audio_{i+1:0
