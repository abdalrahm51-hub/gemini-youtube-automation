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

if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def call_llm_api(prompt):
    """دالة تتصل بـ OpenRouter باستخدام مفتاحك الجديد"""
    api_key = os.environ.get("GOOGLE_API_KEY") 
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ChaitanyaEswarRajeshJakki/gemini-youtube-automation",
        "X-Title": "Unknown Files Automation"
    }
    payload = {
        "model": "google/gemini-3.5-flash", 
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        # محاولة استخدام موديل احتياطي إذا فشل الأول
        payload["model"] = "google/gemini-3.1-flash-lite"
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        raise Exception(f"API Error: {e}")

def get_pexels_image(query, video_type):
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key: return None
    orientation = 'landscape' if video_type == 'long' else 'portrait'
    try:
        headers = {"Authorization": pexels_api_key}
        params = {"query": f"mysterious {query}", "per_page": 1, "orientation": orientation}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
        data = response.json()
        if data.get('photos'):
            img_res = requests.get(data['photos'][0]['src']['large2x'], timeout=15)
            return Image.open(BytesIO(img_res.content)).convert("RGBA")
    except: pass
    return None

def text_to_speech(text, output_path):
    print(f"🎤 Converting script to speech (Arabic)...")
    temp_mp3 = str(output_path).replace('.mp3', '_temp.mp3')
    wav_path = str(output_path.with_suffix('.wav'))
    tts = gTTS(text=text, lang='ar', slow=False)
    tts.save(temp_mp3)
    AudioSegment.from_mp3(temp_mp3).export(wav_path, format="wav")
    os.remove(temp_mp3)
    return Path(wav_path)

def generate_curriculum(previous_titles=None):
    print("🤖 Generating curriculum...")
    prompt = "Generate a JSON with a list of 10 mystery story titles for 'Unknown Files' channel. Respond ONLY with JSON format: {\"lessons\": [{\"chapter\": 1, \"part\": 1, \"title\": \"Title\", \"status\": \"pending\", \"youtube_id\": null}]}"
    text = call_llm_api(prompt)
    clean_text = text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_text)

def generate_lesson_content(lesson_title):
    print(f"🤖 Generating content for: {lesson_title}")
    prompt = f"Create a mystery story in Arabic about '{lesson_title}'. Return JSON with 'long_form_slides' (list of 7 title/content pairs), 'short_form_highlight', and 'hashtags'. Respond ONLY with JSON."
    text = call_llm_api(prompt)
    clean_text = text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_text)

def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumb = thumbnail_title is not None
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    title = thumbnail_title if is_thumb else slide_content.get("title", "")
    bg = get_pexels_image(title, video_type) or Image.new('RGBA', (width, height), (15, 15, 15))
    bg = bg.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
    final = Image.alpha_composite(bg.convert("RGBA"), Image.new('RGBA', bg.size, (0, 0, 0, 180))).convert("RGB")
    draw = ImageDraw.Draw(final)
    draw.text((width//10, height//2), title[:40], fill=(255, 255, 255), font=FALLBACK_THUMBNAIL_FONT)
    path = output_dir / f"{'thumbnail' if is_thumb else f'slide_{slide_number:02d}'}.png"
    final.save(path)
    return str(path)

def create_video(slide_paths, audio_paths, output_path, video_type):
    print(f"🎬 Creating {video_type} video...")
    clips = []
    for img, aud in zip(slide_paths, audio_paths):
        a_clip = AudioFileClip(str(aud))
        i_clip = ImageClip(img).set_duration(a_clip.duration + 0.5).set_audio(a_clip)
        clips.append(i_clip)
    final = concatenate_videoclips(clips, method="compose")
    if BACKGROUND_MUSIC_PATH.exists():
        bg = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.05).fx(vfx.loop, duration=final.duration)
        final = final.set_audio(CompositeAudioClip([final.audio, bg]))
    final.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
    print(f"✅ Video created: {output_path}")
