import os
import json
import urllib.request
import urllib.error
import logging

from datetime import datetime

from shared.history_service import save_message, get_history
from shared.prompts import rules
from shared.google_calendar import (
    book_appointment_google,
    remove_appointment_google
)

logger = logging.getLogger()

GEMINI_TOKEN = os.environ.get("GEMINI_TOKEN", "")


def call_gemini(chat_id: str, user_message: str) -> str:

    # Guardar mensaje usuario
    save_message(chat_id, 'user', user_message)

    # Historial
    history = get_history(chat_id, limit=10)

    contents = [
        {
            "parts": [{"text": msg['message']}],
            "role": "user" if msg['role'] == "user" else "model"
        }
        for msg in history
    ]

    # Fecha/hora actual
    now = datetime.now()

    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    dia_semana = now.strftime("%A")

    # Prompt sistema
    system_prompt = (
        f"{rules}\n\n"
        f"Fecha actual: {current_date}\n"
        f"Hora actual: {current_time}\n"
        f"Día actual: {dia_semana}\n\n"
        f"INSTRUCCIONES DE HERRAMIENTAS:\n"
        f"- Usa 'book_appointment' para crear citas.\n"
        f"- Usa 'remove_book_appointment' para eliminar citas."
    )

    # URL Gemini
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={GEMINI_TOKEN}"
    )

    # Tools Gemini
    tools = [
        {
            "functionDeclarations": [
                {
                    "name": "book_appointment",
                    "description": "Agenda una cita en Google Calendar.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "fecha": {
                                "type": "STRING",
                                "description": "Formato YYYY-MM-DD"
                            },
                            "hora": {
                                "type": "STRING",
                                "description": "Formato HH:mm"
                            },
                            "motivo": {
                                "type": "STRING",
                                "description": "Descripción breve"
                            }
                        },
                        "required": [
                            "fecha",
                            "hora",
                            "motivo"
                        ]
                    }
                },
                {
                    "name": "remove_book_appointment",
                    "description": "Elimina una cita existente.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "fecha": {
                                "type": "STRING",
                                "description": "Formato YYYY-MM-DD"
                            },
                            "hora": {
                                "type": "STRING",
                                "description": "Formato HH:mm"
                            }
                        },
                        "required": [
                            "fecha",
                            "hora"
                        ]
                    }
                }
            ]
        }
    ]

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": system_prompt
                }
            ]
        },
        "contents": contents,
        "tools": tools,
        "toolConfig": {
            "functionCallingConfig": {
                "mode": "AUTO"
            }
        },
        "generationConfig": {
            "temperature": 0.1
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    }

    body = json.dumps(payload).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Content-Type': 'application/json'
        }
    )

    try:

        with urllib.request.urlopen(req) as resp:

            result = json.loads(
                resp.read().decode('utf-8')
            )

            candidate = result['candidates'][0]

            # Safety
            if candidate.get('finishReason') == 'SAFETY':

                response_text = (
                    "Lo siento, no puedo responder a ese tipo de mensajes."
                )

            else:

                content = candidate['content']

                parts = content.get('parts', [])

                response_text = (
                    "No pude procesar tu solicitud."
                )

                for part in parts:

                    # Function call
                    if "functionCall" in part:

                        function_call = part["functionCall"]

                        function_name = function_call["name"]

                        args = function_call.get("args", {})

                        date = args.get("fecha")
                        hora = args.get("hora")
                        motivo = args.get(
                            "motivo",
                            "Cita por Chatbot"
                        )
                        # BOOK
                        if function_name == "book_appointment":
                            success, payload = (
                                book_appointment_google(
                                    date,
                                    hora,
                                    motivo
                                )
                            )
                            if success:
                                response_text = (
                                f"✅ Tu cita fue agendada para el "
                                f"{date} a las {hora}."
                            )

                            if payload.get("code") == "SLOT_OCCUPIED":
                                response_text = (
                                    f"❌ El horario del {date} a las {hora} no está disponible. "
                                    f"Por favor, elige otro horario."
                                )
                                continue
                            response_text = f"❌ Error al agendar: {payload.get('message')}"

                        # REMOVE
                        elif function_name == "remove_book_appointment":
                            success, payload = (
                                remove_appointment_google(
                                    date,
                                    hora
                                )
                            )

                            response_text = (
                                f"🗑️ Eliminé tu cita del "
                                f"{date} a las {hora}."
                                if success
                                else (
                                    f"❌ No pude eliminar la cita: "
                                    f"{payload.get('message')}"
                                )
                            )

                        else:

                            response_text = (
                                "La herramienta solicitada no es válida."
                            )

                    # Texto normal
                    elif "text" in part:

                        response_text = part["text"]

    except urllib.error.HTTPError as e:

        error_body = e.read().decode('utf-8')

        logger.error(
            f"Gemini HTTP {e.code}: {error_body}"
        )

        try:

            error_json = json.loads(error_body)

            error_message = (
                error_json
                .get("error", {})
                .get("message", "")
            )

            if "API key not valid" in error_message:

                response_text = (
                    "La API key de Gemini es inválida."
                )

            elif "quota" in error_message.lower():

                response_text = (
                    "Se alcanzó el límite de Gemini."
                )

            else:

                response_text = (
                    "Hubo un problema con Gemini."
                )

        except Exception:

            response_text = (
                "Hubo un problema con Gemini."
            )

    except Exception as e:

        logger.error(
            f"Error inesperado Gemini: {str(e)}"
        )

        response_text = (
            "Tengo problemas técnicos para procesar tu solicitud."
        )

    # Guardar respuesta
    save_message(chat_id, 'assistant', response_text)

    return response_text