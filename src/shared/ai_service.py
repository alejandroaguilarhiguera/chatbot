import os
import json
import urllib.request
import logging

from shared.history_service import save_message, get_history
from shared.prompts import rules

logger = logging.getLogger()


def call_groq(chat_id: str, user_message: str, model="llama-3.1-8b-instant", tools=None):
    save_message(chat_id, 'user', user_message)

    history = get_history(chat_id, limit=10)
    messages = [
        {
            "role": msg['role'],  # 'user' o 'assistant' directo
            "content": msg['message']
        }
        for msg in history
    ]

    # Inyectar system prompt al inicio
    messages.insert(0, {"role": "system", "content": rules})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
        "User-Agent": "MyCustomBot/1.0 (Contact: alejandro.aguilar.higuera@gmail.com)"
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            response_text = result['choices'][0]['message']['content']

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Groq HTTP {e.code}: {error_body}")
        response_text = "Lo siento, tuve un problema al procesar tu mensaje."

    except Exception as e:
        logger.error(f"Error inesperado en Groq API: {str(e)}")
        response_text = "Lo siento, tuve un problema al procesar tu mensaje."

    save_message(chat_id, 'assistant', response_text)
    return response_text

GEMINI_TOKEN = os.environ.get("GEMINI_TOKEN", "")
def get_gemini_response(user_message):
    """Llamada a la API de Gemini usando urllib"""

def get_gemini_response(chat_id: str, user_message: str) -> str:

    save_message(chat_id, 'user', user_message)

    history = get_history(chat_id, limit=10)
    contents = [
        {
            "parts": [{"text": msg['message']}],
            "role": "user" if msg['role'] == "user" else "model"
        }
        for msg in history
    ]

    GEMINI_TOKEN = os.environ.get("GEMINI_TOKEN", "")
    # 👇 url debe estar FUERA del try
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_TOKEN}"

    payload = {
        "systemInstruction": {
            "parts": [{ "text": rules }]
        },
        "contents": contents,
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
    }

    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            candidate = result['candidates'][0]

            if candidate.get('finishReason') == 'SAFETY':
                return "Lo siento, no puedo responder a ese tipo de mensajes."

            response_text = candidate['content']['parts'][0]['text']

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Gemini HTTP {e.code}: {error_body}")
        response_text = "Lo siento, tuve un problema al procesar tu mensaje."

    except Exception as e:
        logger.error(f"Error inesperado en Gemini API: {str(e)}")
        response_text = "Lo siento, tuve un problema al procesar tu mensaje."

    save_message(chat_id, 'assistant', response_text)
    return response_text
