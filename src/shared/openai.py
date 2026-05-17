import os
import json
import urllib.request
import logging
from datetime import datetime
from shared.history_service import save_message, get_history
from shared.prompts import rules
from shared.google_calendar import (
    book_appointment_google,
    remove_appointment_google,
    get_calendar_events_google
)

logger = logging.getLogger()

OPENAI_TOKEN = os.environ.get("OPENAI_TOKEN", "")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {OPENAI_TOKEN}"
}
URL = "https://api.openai.com/v1/chat/completions"

def get_date_now():
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    day_week = now.strftime("%A")
    return current_date, current_time, day_week

def get_response_openai(user_message: str, model="gpt-4.1-mini") -> tuple[bool, str]:
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {
                "role": "system",
                "content": rules
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
        logger.error(f"HTTP Error OpenAI: {e.code} - {error_body}")
        return False, "Error de comunicación con OpenAI."

    except Exception as e:
        logger.error(f"Error OpenAI: {str(e)}")
        return False, "Error interno al procesar la respuesta."

def call_openai(channel: str, chat_id: str, user_message: str, model="gpt-4.1-mini"):
    save_message(channel, chat_id, 'user', user_message)
    history = get_history(chat_id, limit=10)
    messages = [
        {
            "role": msg['role'],
            "content": msg['message']
        }
        for msg in history
    ]

    current_date, current_time, day_week = get_date_now()

    system_message = (
        f"{rules}\n\n"
        f"Fecha actual: {current_date}\n"
        f"Hora actual: {current_time}\n"
        f"Día actual: {day_week}\n\n"
        f"INSTRUCCIONES DE HERRAMIENTAS:\n"
        f"- Usa 'book_appointment' para crear citas.\n"
        f"- Usa 'remove_book_appointment' para eliminar citas."
    )

    messages.insert(0, {
        "role": "system",
        "content": system_message
    })

    # Tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Agenda una cita en Google Calendar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {
                            "type": "string",
                            "description": "Formato YYYY-MM-DD"
                        },
                        "hora": {
                            "type": "string",
                            "description": "Formato HH:mm"
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Descripción breve"
                        }
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
                        "fecha": {
                            "type": "string",
                            "description": "Formato YYYY-MM-DD"
                        },
                        "hora": {
                            "type": "string",
                            "description": "Formato HH:mm"
                        }
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

        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            URL,
            data=body,
            headers=headers
        )

        with urllib.request.urlopen(req) as resp:

            result = json.loads(resp.read().decode("utf-8"))

            message = result["choices"][0]["message"]

            # Tool calls
            if message.get("tool_calls"):

                tool_call = message["tool_calls"][0]

                function_name = tool_call["function"]["name"]

                args = json.loads(
                    tool_call["function"]["arguments"]
                )

                date = args.get("fecha")
                hour = args.get("hora")
                reason = args.get("motivo", "Cita por Chatbot")

                if function_name == "book_appointment":
                    success, payload = book_appointment_google(
                        date,
                        hour,
                        reason
                    )

                    if success:
                        prompt_result = (
                            "Genera una respuesta corta y amigable para el usuario "
                            "basada en el resultado de agendar una cita.\n\n"
                            f"success={success}\n"
                            f"payload={json.dumps(payload, ensure_ascii=False)}"
                        )

                        ok, response_text = get_response_openai(
                            prompt_result
                        )

                    elif success == False and payload.get("code") == "SLOT_OCCUPIED":
                        success_events, events = get_calendar_events_google(f"{date} {hour}")

                        if success_events:
                            prompt_result = (
                                "Genera una respuesta corta y amigable para el usuario "
                                "La fecha y hora en la que el usuario intentó agendar una cita esta ocupada {date} {hour} "
                                "ofrece otra fecha y hora disponible que puede agendar, te muestro los eventos que estan ocupados.\n\n"
                                f"events={json.dumps(events, ensure_ascii=False)}"
                            )
                        else:
                            prompt_result = (
                                "Genera una respuesta corta y amigable para el usuario "
                                "La fecha en la que el usuario intentó agendar una cita esta ocupada {date} {hour}. "
                            )
                        ok, response_text = get_response_openai(prompt_result)

                    else:
                        response_text = "Hubo un error al intentar agendar la cita."

                elif function_name == "remove_book_appointment":

                    success, payload = remove_appointment_google(
                        date,
                        hour
                    )
                    prompt_result = (
                        "Genera una respuesta corta y amigable para el usuario "
                        "basada en el resultado de eliminar una cita.\n\n"
                        f"success={success}\n"
                        f"payload={json.dumps(payload, ensure_ascii=False)}"
                    )
                    ok, response_text = get_response_openai(
                        prompt_result
                    )
                else:
                    response_text = "La herramienta solicitada no es válida."
            else:
                response_text = message.get(
                    "content",
                    "No pude procesar tu solicitud."
                )


    except urllib.error.HTTPError as e:

        error_body = e.read().decode("utf-8")

        logger.error(
            f"OpenAI HTTP {e.code}: {error_body}"
        )

        try:
            error_json = json.loads(error_body)

            error_code = (
                error_json
                .get("error", {})
                .get("code")
            )

            if error_code == "billing_not_active":
                response_text = (
                    "La cuenta de OpenAI no tiene billing activo."
                )

            elif error_code == "invalid_api_key":
                response_text = (
                    "La API key de OpenAI es inválida."
                )

            else:
                response_text = (
                    "Hubo un problema con OpenAI."
                )

        except Exception:
            response_text = (
                "Hubo un problema con OpenAI."
            )
    except Exception as e:

        logger.error(
            f"Error OpenAI: {str(e)}"
        )

        response_text = (
            "Tengo problemas técnicos para procesar tu solicitud."
        )

    save_message(channel, chat_id, 'assistant', response_text)

    return response_text