import os
import json
import requests
from io import BytesIO
import google.generativeai as genai  # استخدام الطريقة التقليدية الأكثر استقراراً
from gtts import gTTS
from moviepy.editor import AudioFileClip, ImageClip, CompositeAudioClip, concatenate_videoclips
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
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key: return None
    orientation = 'landscape' if video_type == 'long' else 'portrait'
    try:
        headers = {"Authorization": pexels_api_key}
        params = {"query": f"mysterious {query}", "per_page": 1, "orientation": orientation}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('photos'):
                img_url = data['photos'][0]['src']['large2x']
                img_res = requests.get(img_url, timeout=15)
                return Image.open(BytesIO(img_res.content)).convert("RGBA")
    except: pass
    return None

def text_to_speech(text, output_path):
    try:
        temp_mp3 = str(output_path).replace('.mp3', '_temp.mp3')
        wav_path = str(output_path.with_suffix('.wav'))
        tts = gTTS(text=text, lang='ar', slow=False)
        tts.save(temp_mp3)
        audio = AudioSegment.from_mp3(temp_mp3)
        audio.export(wav_path, format="wav")
        os.remove(temp_mp3)
        return Path(wav_path)
    except Exception as e:
        print(f"TTS Error: {e}")
        raise

def call_gemini(prompt):
    """دالة ذكية لتجربة الاتصال بجوجل بأكثر من طريقة لتفادي خطأ 404"""
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    # تجربة الموديلات المتاحة بالترتيب
    models_to_try = ['gemini-1.5-flash', 'gemini-pro']
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Trying {model_name} failed: {e}")
            continue
    raise Exception("All Gemini models failed. Check your API key and quota.")

def generate_curriculum(previous_titles=None):
    print("🤖 Generating curriculum...")
    prompt = "Generate a JSON with a list of 10 mysterious stories. Format: {'lessons': [{'chapter': 1, 'part': 1, 'title': 'Story Title', 'status': 'pending', 'youtube_id': null}]}. Return ONLY JSON."
    response_text = call_gemini(prompt)
    json_string = response_text.strip().replace("```json", "").replace("```", "")
    return json.loads(json_string)

def generate_lesson_content(lesson_title):
    print(f"🤖 Generating content for: {lesson_title}")
    prompt = f"Write a mysterious story about '{lesson_title}' in Arabic. Return JSON with: 'long_form_slides' (list of 5 slides with 'title' and 'content'), 'short_form_highlight', and 'hashtags'."
    response_text = call_gemini(prompt)
    json_string = response_text.strip().replace("```json", "").replace("```", "")
    return json.loads(json_string)

def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
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
    path = output_dir / f"{'thumbnail' if is_thumbnail else f'slide_{slide_number}'}.png"
    final_bg.save(path)
    return str(path)

def create_video(output_path, slides_content, audio_paths, video_type):
    print(f"🎬 Creating video: {output_path}")
    clips = []
    for i, (slide, audio_p) in enumerate(zip(slides_content, audio_paths)):
        img_p = generate_visuals(Path("temp_visuals"), video_type, slide_content=slide, slide_number=i+1)
        audio_clip = AudioFileClip(str(audio_p))
        img_clip = ImageClip(img_p).set_duration(audio_clip.duration).set_audio(audio_clip)
        clips.append(img_clip)
    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
