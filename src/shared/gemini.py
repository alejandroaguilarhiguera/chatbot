import os
import json
import urllib.request
import urllib.error
import logging
from shared.get_date_now import get_date_now

from shared.history_service import save_message, get_history
from shared.prompts import rules
from shared.google_calendar import (
    book_appointment_google,
    remove_appointment_google,
    get_calendar_events_google
)

logger = logging.getLogger()

GEMINI_TOKEN = os.environ.get("GEMINI_TOKEN", "")

def get_response_gemini(user_message: str) -> tuple[bool, str]:
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={GEMINI_TOKEN}"
    )

    payload = {
        "systemInstruction": {
            "parts": [{"text": rules}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_message}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1
        }
    }

    try:
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=body,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            candidate = result['candidates'][0]
            
            if candidate.get('finishReason') == 'SAFETY':
                return False, "Lo siento, no puedo responder por filtros de seguridad."
            
            content = candidate.get('content', {})
            parts = content.get('parts', [])
            
            if parts and "text" in parts[0]:
                return True, parts[0]["text"]
            
            return True, ""

    except Exception as e:
        logger.error(f"Error Gemini Gen: {str(e)}")
        return False, "Error interno al procesar la respuesta."


def call_gemini(channel: str, chat_id: str, user_message: str) -> str:
    # 1. Guardar mensaje usuario y recuperar historial
    save_message(channel, chat_id, 'user', user_message)
    history = get_history(chat_id, limit=10)

    contents = [
        {
            "parts": [{"text": msg['message']}],
            "role": "user" if msg['role'] == "user" else "model"
        }
        for msg in history
    ]

    # 2. Contexto Temporal
    current_date, current_time, day_week = get_date_now()

    system_prompt = (
        f"{rules}\n\n"
        f"Fecha actual: {current_date}\n"
        f"Hora actual: {current_time}\n"
        f"Día actual: {day_week}\n\n"
        f"INSTRUCCIONES DE HERRAMIENTAS:\n"
        f"- Usa 'book_appointment' para crear citas.\n"
        f"- Usa 'remove_book_appointment' para eliminar citas."
    )

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={GEMINI_TOKEN}"
    )

    # 3. Herramientas Gemini
    tools = [
        {
            "functionDeclarations": [
                {
                    "name": "book_appointment",
                    "description": "Agenda una cita en Google Calendar.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "fecha": {"type": "STRING", "description": "Formato YYYY-MM-DD"},
                            "hora": {"type": "STRING", "description": "Formato HH:mm"},
                            "motivo": {"type": "STRING", "description": "Descripción breve"}
                        },
                        "required": ["fecha", "hora", "motivo"]
                    }
                },
                {
                    "name": "remove_book_appointment",
                    "description": "Elimina una cita existente.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "fecha": {"type": "STRING", "description": "Formato YYYY-MM-DD"},
                            "hora": {"type": "STRING", "description": "Formato HH:mm"}
                        },
                        "required": ["fecha", "hora"]
                    }
                }
            ]
        }
    ]

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "tools": tools,
        "toolConfig": {
            "functionCallingConfig": {"mode": "AUTO"}
        },
        "generationConfig": {
            "temperature": 0.1
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
    }

    try:
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=body,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            candidate = result['candidates'][0]

            if candidate.get('finishReason') == 'SAFETY':
                response_text = "Lo siento, no puedo responder a ese tipo de mensajes por políticas de seguridad."
            else:
                content = candidate['content']
                parts = content.get('parts', [])
                response_text = "No pude procesar tu solicitud."

                for part in parts:
                    # Llamada a herramientas
                    if "functionCall" in part:
                        function_call = part["functionCall"]
                        function_name = function_call["name"]
                        args = function_call.get("args", {})

                        date = args.get("fecha")
                        hora = args.get("hora")
                        motivo = args.get("motivo", "Cita por Chatbot")

                        if function_name == "book_appointment":
                            success, payload_resp = book_appointment_google(date, hora, motivo)
                            
                            if success:
                                prompt_result = (
                                    "Genera una respuesta corta y amigable para el usuario "
                                    "basada en el resultado de agendar una cita.\n\n"
                                    f"success={success}\n"
                                    f"payload={json.dumps(payload_resp, ensure_ascii=False)}"
                                )
                                ok, response_text = get_response_gemini(prompt_result)

                            elif success == False and payload_resp.get("code") == "SLOT_OCCUPIED":
                                success_events, events = get_calendar_events_google(f"{date} {hora}")

                                if success_events:
                                    prompt_result = (
                                        "Genera una respuesta corta y amigable para el usuario "
                                        f"La fecha y hora en la que el usuario intentó agendar una cita esta ocupada {date} {hora} "
                                        "ofrece otra fecha y hora disponible que puede agendar, te muestro los eventos que estan ocupados.\n\n"
                                        f"events={json.dumps(events, ensure_ascii=False)}"
                                    )
                                else:
                                    prompt_result = (
                                        "Genera una respuesta corta y amigable para el usuario "
                                        f"La fecha en la que el usuario intentó agendar una cita esta ocupada {date} {hora}. "
                                    )
                                ok, response_text = get_response_gemini(prompt_result)

                            else:
                                response_text = "Hubo un error al intentar agendar la cita."

                        elif function_name == "remove_book_appointment":
                            success, payload_resp = remove_appointment_google(date, hora)
                            prompt_result = (
                                "Genera una respuesta corta y amigable para el usuario "
                                "basada en el resultado de eliminar una cita.\n\n"
                                f"success={success}\n"
                                f"payload={json.dumps(payload_resp, ensure_ascii=False)}"
                            )
                            ok, response_text = get_response_gemini(prompt_result)

                        else:
                            response_text = "La herramienta solicitada no es válida."

                    # Texto normal
                    elif "text" in part:
                        response_text = part["text"]

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Gemini HTTP {e.code}: {error_body}")
        
        try:
            error_json = json.loads(error_body)
            error_message = error_json.get("error", {}).get("message", "")
            
            if "API key not valid" in error_message:
                response_text = "La API key de Gemini es inválida."
            elif "quota" in error_message.lower():
                response_text = "Se alcanzó el límite de Gemini."
            else:
                response_text = "Hubo un problema con Gemini."
        except Exception:
            response_text = "Hubo un problema con Gemini."

    except Exception as e:
        logger.error(f"Error inesperado Gemini: {str(e)}")
        response_text = "Tengo problemas técnicos para procesar tu solicitud."

    # 4. Guardar respuesta
    save_message(channel, chat_id, 'assistant', response_text)

    return response_text