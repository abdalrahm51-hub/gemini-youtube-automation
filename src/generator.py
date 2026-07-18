import os
import json
import requests
from pathlib import Path

def call_gemini_api(prompt):
    """
    تعديل نهائي ومستقر باستخدام خوادم OpenRouter المجانية لتخطي أخطاء الـ Rate Limit 
    وتعلق الحسابات تماماً.
    """
    raw_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not raw_api_key:
        raise ValueError("❌ لم يتم العثور على مفتاح API في إعدادات جيت هاب!")

    api_key = raw_api_key.strip().strip('{}').strip('"').strip("'")

    # رابط الاتصال الموحد والمستقر
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta-llama/llama-3-8b-instruct:free", # نموذج فائق الذكاء ومجاني بالكامل
        "messages": [
            {
                "role": "user",
                "content": prompt + "\nRespond with raw JSON only. Do not wrap in markdown tags."
            }
        ]
    }

    try:
        print("📡 يرسل الطلب الآن عبر الرابط البديل والمستقر (OpenRouter)...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        text_content = result['choices'][0]['message']['content']
        return text_content
    except Exception as e:
        raise RuntimeError(f"❌ فشل الاتصال بالخادم: {e}")
