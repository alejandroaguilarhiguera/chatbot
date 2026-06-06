import os
import json
import urllib.request
import logging
from datetime import datetime

from shared.history_service import save_message, get_history
from shared.google_calendar.book_appointment_google import book_appointment_google
from shared.google_calendar.remove_appointment_google import remove_appointment_google
from shared.google_calendar.get_calendar_events_google import get_calendar_events_google 


logger = logging.getLogger()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "User-Agent": "MyCustomBot/1.0"
}
URL = "https://api.groq.com/openai/v1/chat/completions"

def get_date_now():
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    day_week = now.strftime("%A")
    return current_date, current_time, day_week

def get_response_groq(user_message: str, prompt: str, model="llama-3.3-70b-versatile") -> tuple[bool, str]:
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            URL,
            data=body,
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))
            message = result["choices"][0]["message"]
            return True, message.get("content", "")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"HTTP Error Groq: {e.code} - {error_body}")
        return False, "Error de comunicación con Groq."

    except Exception as e:
        logger.error(f"Error Groq: {str(e)}")
        return False, "Error interno al procesar la respuesta."


def call_groq(data, message_history, model="llama-3.3-70b-versatile"):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Agenda una cita en el calendario de Google.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {"type": "string", "description": "Formato YYYY-MM-DD"},
                        "hora": {"type": "string", "description": "Formato HH:mm"},
                        "motivo": {"type": "string", "description": "Descripción breve"}
                    },
                    "required": ["fecha", "hora", "motivo"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "remove_book_appointment",
                "description": "Elimina una cita existente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {"type": "string", "description": "Formato YYYY-MM-DD"},
                        "hora": {"type": "string", "description": "Formato HH:mm"}
                    },
                    "required": ["fecha", "hora"]
                }
            }
        }
    ]

    payload = {
        "model": model,
        "messages": message_history,
        "temperature": 0.1,
        "tools": tools,
        "tool_choice": "auto"
    }

    try:
        print("Payload Groq:", str(payload))
        req = urllib.request.Request(
            URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            message = result['choices'][0]['message']
            return message

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Groq HTTP {e.code}: {error_body}")
        
        try:
            error_json = json.loads(error_body)
            error_message = error_json.get("error", {}).get("message", "")
            if "invalid api key" in error_message.lower():
                response_text = "La API key de Groq es inválida."
            else:
                response_text = "Hubo un problema con Groq."
        except Exception:
            response_text = "Hubo un problema con la API de Groq."
            
    except Exception as e:
        logger.error(f"Error Groq: {str(e)}")
        response_text = "Tengo problemas técnicos para procesar tu solicitud."

    return {"content":response_text}


def analyze_image_groq(image_data, model="meta-llama/llama-4-scout-17b-16e-instruct"):
    prompt = (
        "Eres un asistente inteligente que analiza imágenes enviadas por los usuarios y proporciona una descripción detallada de lo que hay en la imagen. "
        "Cuando recibas una imagen, responde con una descripción clara y concisa de su contenido, incluyendo objetos, personas, acciones y cualquier detalle relevante que puedas identificar. "
        "Si la imagen es difícil de interpretar, haz tu mejor esfuerzo para describir lo que ves."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Analiza esta imagen: {image_data.url}"}
        ],
        "temperature": 0.1,
    }

    try:
        req = urllib.request.Request(
            URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']

    except Exception as e:
        logger.error(f"Error al analizar imagen con Groq: {str(e)}")
        return "No pude analizar la imagen correctamente."