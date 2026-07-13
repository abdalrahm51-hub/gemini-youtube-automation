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

        # تم الضبط للغة العربية
        tts = gTTS(text=text, lang='ar', slow=False)
        tts.save(temp_mp3_path)

        audio = AudioSegment.from_mp3(temp_mp3_path)
        audio.export(wav_path, format="wav")
        os.remove(temp_mp3_path)

        print(f"✅ Speech generated successfully!")
        return Path(wav_path)
    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise

def generate_curriculum(previous_titles=None):
    """Generates the entire course curriculum using Gemini."""
    print("🤖 Generating new curriculum...")
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        prompt = f"""
        You are an expert storyteller for a YouTube channel called 'Unknown Files'. 
        Generate a list of 10 mysterious, unsolved crimes or shocking facts stories.
        Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 10 lesson objects.
        Each lesson object must have: "chapter", "part", "title", "status" (pending), and "youtube_id" (null).
        """
        # التصحيح: gemini-1.5-flash
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_string)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Failed to generate curriculum. {e}")
        raise

def generate_lesson_content(lesson_title):
    """Generates the content for one mystery story."""
    print(f"🤖 Generating content for: '{lesson_title}'...")
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        prompt = f"""
        Write a mysterious story about '{lesson_title}' in Arabic. 
        Generate a JSON response with:
        1. "long_form_slides": A list of 5-7 slide objects (title and content in Arabic).
        2. "short_form_highlight": A punchy 1-2 sentence summary in Arabic.
        3. "hashtags": 5-7 relevant hashtags.
        Return only valid JSON.
        """
        # التصحيح: gemini-1.5-flash
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_string)
    except Exception as e:
        print(f"❌ ERROR: Failed to generate content: {e}")
        raise

def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    """Generates a professional slide or thumbnail."""
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    bg_image = get_pexels_image(title, video_type)

    if not bg_image:
        bg_image = Image.new('RGBA', (width, height), color=(12, 17, 29))
    bg_image = bg_image.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
    darken_layer = Image.new('RGBA', bg_image.size, (0, 0, 0, 180))
    final_bg = Image.alpha_composite(bg_image, darken_layer).convert("RGB")
    draw = ImageDraw.Draw(final_bg)

    # محاولة استخدام الخطوط العربية إذا وجدت
    draw.text((width//10, height//2), title[:40], fill=(255, 255, 255))
    
    file_prefix = "thumbnail" if is_thumbnail else f"slide_{slide_number:02d}"
    path = output_dir / f"{file_prefix}.png"
    final_bg.save(path)
    return str(path)

def create_video(output_path, slides_content, audio_paths, video_type):
    """Combines images and audio into a final video file."""
    print(f"🎬 Creating {video_type} video...")
    clips = []
    for i, (slide, audio_p) in enumerate(zip(slides_content, audio_paths)):
        img_path = generate_visuals(Path("temp_visuals"), video_type, slide_content=slide, slide_number=i+1, total_slides=len(slides_content))
        audio_clip = AudioFileClip(str(audio_p))
        img_clip = ImageClip(img_path).set_duration(audio_clip.duration).set_audio(audio_clip)
        clips.append(img_clip)
    
    final_video = concatenate_videoclips(clips, method="compose")
    
    # إضافة موسيقى خلفية إذا وجدت
    if BACKGROUND_MUSIC_PATH.exists():
        bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.1).set_duration(final_video.duration)
        final_audio = CompositeAudioClip([final_video.audio, bg_music])
        final_video = final_video.set_audio(final_audio)
        
    final_video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
    print(f"✅ Video created: {output_path}")
