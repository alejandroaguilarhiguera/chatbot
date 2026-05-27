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


def call_groq(data, model="llama-3.3-70b-versatile"):
    # 1. Historial
    channel = data.channel
    phone_id = data.phone_id
    prompt = data.prompt
    save_message(channel, phone_id, 'user', data.message)
    history = get_history(phone_id, limit=10)
    
    messages = [
        {"role": msg['role'], "content": msg['message']}
        for msg in history
    ]
    
    messages.insert(0, {"role": "system", "content": prompt})

    # 3. Herramientas
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
        "messages": messages,
        "temperature": 0.1,
        "tools": tools,
        "tool_choice": "auto"
    }

    try:
        req = urllib.request.Request(
            URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            message = result['choices'][0]['message']

            # Procesamiento de llamadas a herramientas
            if message.get("tool_calls"):
                tool_call = message['tool_calls'][0]
                function_name = tool_call['function']['name']
                args = json.loads(tool_call['function']['arguments'])
                
                date = args.get('fecha')
                hour = args.get('hora')
                reason = args.get('motivo', 'Cita por Chatbot')

                if function_name == "book_appointment":
                    success, payload = book_appointment_google(date, hour, reason)

                    if success:
                        prompt_result = (
                            "Genera una respuesta corta y amigable para el usuario "
                            "basada en el resultado de agendar una cita.\n\n"
                            f"success={success}\n"
                            f"payload={json.dumps(payload, ensure_ascii=False)}"
                        )
                        ok, response_text = get_response_groq(prompt_result, prompt, model)

                    elif success == False and payload.get("code") == "SLOT_OCCUPIED":
                        success_events, events = get_calendar_events_google(f"{date} {hour}")

                        if success_events:
                            prompt_result = (
                                "Genera una respuesta corta y amigable para el usuario "
                                f"La fecha y hora en la que el usuario intentó agendar una cita esta ocupada {date} {hour} "
                                "ofrece otra fecha y hora disponible que puede agendar, te muestro los eventos que estan ocupados.\n\n"
                                f"events={json.dumps(events, ensure_ascii=False)}"
                            )
                        else:
                            prompt_result = (
                                "Genera una respuesta corta y amigable para el usuario "
                                f"La fecha en la que el usuario intentó agendar una cita esta ocupada {date} {hour}. "
                            )
                        ok, response_text = get_response_groq(prompt_result, prompt, model)

                    else:
                        response_text = "Hubo un error al intentar agendar la cita."
                
                elif function_name == "remove_book_appointment":
                    success, payload = remove_appointment_google(date, hour)
                    
                    prompt_result = (
                        "Genera una respuesta corta y amigable para el usuario "
                        "basada en el resultado de eliminar una cita.\n\n"
                        f"success={success}\n"
                        f"payload={json.dumps(payload, ensure_ascii=False)}"
                    )
                    ok, response_text = get_response_groq(prompt_result, prompt, model)
                    
                else:
                    response_text = "La herramienta solicitada no es válida."
            else:
                response_text = message.get('content', "No pude procesar tu solicitud.")

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

    # Se agregó 'channel' para igualar el guardado de historial de tu script OpenAI
    save_message(channel, phone_id, 'assistant', response_text)
    return response_text