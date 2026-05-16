import os
import json
import urllib.request
import logging
from datetime import datetime
from shared.history_service import save_message, get_history
from shared.prompts import rules
from shared.google_calendar import (
    book_appointment_google,
    remove_appointment_google
)

logger = logging.getLogger()

OPENAI_TOKEN = os.environ.get("OPENAI_TOKEN", "")

def call_openai(chat_id: str, user_message: str, model="gpt-4.1-mini"):

    # Guardar mensaje usuario
    save_message(chat_id, 'user', user_message)

    # Historial
    history = get_history(chat_id, limit=10)

    messages = [
        {
            "role": msg['role'],
            "content": msg['message']
        }
        for msg in history
    ]

    # Fecha/hora actual
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    dia_semana = now.strftime("%A")

    # Prompt sistema
    system_message = (
        f"{rules}\n\n"
        f"Fecha actual: {current_date}\n"
        f"Hora actual: {current_time}\n"
        f"Día actual: {dia_semana}\n\n"
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

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_TOKEN}"
    }

    try:

        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
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

                fecha = args.get("fecha")
                hora = args.get("hora")
                motivo = args.get("motivo", "Cita por Chatbot")

                if function_name == "book_appointment":

                    exito, detalle = book_appointment_google(
                        fecha,
                        hora,
                        motivo
                    )

                    response_text = (
                        f"✅ Tu cita fue agendada para el {fecha} a las {hora}."
                        if exito
                        else f"❌ Error al agendar: {detalle}"
                    )

                elif function_name == "remove_book_appointment":

                    exito, detalle = remove_appointment_google(
                        fecha,
                        hora
                    )

                    response_text = (
                        f"🗑️ Eliminé tu cita del {fecha} a las {hora}."
                        if exito
                        else f"❌ No pude eliminar la cita: {detalle}"
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

    save_message(chat_id, 'assistant', response_text)

    return response_text