import os
import json
import urllib.request
import logging
from datetime import datetime
from shared.history_service import save_message, get_history
from shared.messages import get_message 
from shared.google_calendar import (
    book_appointment_google,
    remove_appointment_google,
    get_calendar_events_google
)

logger = logging.getLogger()
lang = "es"

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

def get_response_openai(user_message: str, prompt: str, model="gpt-4.1-mini") -> tuple[bool, str]:
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
        logger.error(f"HTTP Error OpenAI: {e.code} - {error_body}")
        return False, get_message("technical_error", lang)

    except Exception as e:
        logger.error(f"Error OpenAI: {str(e)}")
        return False, get_message("technical_error", lang)

def call_openai(data, history_message, model="gpt-4.1-mini"):
    messages = [
        {
            "role": msg['role'],
            "content": msg['message']
        }
        for msg in history_message
    ]

    messages.insert(0, {
        "role": "system",
        "content": data.prompt
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

            return result["choices"][0]["message"]
            # Tool calls
            # if message.get("tool_calls"):

            #     tool_call = message["tool_calls"][0]

            #     function_name = tool_call["function"]["name"]

            #     args = json.loads(
            #         tool_call["function"]["arguments"]
            #     )

            #     date = args.get("fecha")
            #     hour = args.get("hora")
            #     reason = args.get("motivo", "Cita por Chatbot")

            #     if function_name == "book_appointment":
            #         success, payload = book_appointment_google(
            #             date,
            #             hour,
            #             reason
            #         )

            #         if success:
            #             prompt_result = (
            #                 "Genera una respuesta corta y amigable para el usuario "
            #                 "basada en el resultado de agendar una cita.\n\n"
            #                 f"success={success}\n"
            #                 f"payload={json.dumps(payload, ensure_ascii=False)}"
            #             )

            #             ok, response_text = get_response_openai(prompt_result, data.prompt)

            #         elif success == False and payload.get("code") == "SLOT_OCCUPIED":
            #             success_events, events = get_calendar_events_google(f"{date} {hour}")

            #             if success_events:
            #                 prompt_result = (
            #                     "Genera una respuesta corta y amigable para el usuario "
            #                     "La fecha y hora en la que el usuario intentó agendar una cita esta ocupada {date} {hour} "
            #                     "ofrece otra fecha y hora disponible que puede agendar, te muestro los eventos que estan ocupados.\n\n"
            #                     f"events={json.dumps(events, ensure_ascii=False)}"
            #                 )
            #             else:
            #                 prompt_result = (
            #                     "Genera una respuesta corta y amigable para el usuario "
            #                     "La fecha en la que el usuario intentó agendar una cita esta ocupada {date} {hour}. "
            #                 )
            #             ok, response_text = get_response_openai(prompt_result, data.prompt)

            #         else:
            #             logger.error("Hubo un error al intentar agendar la cita.")
            #             response_text = get_message("error_book", lang)

            #     elif function_name == "remove_book_appointment":

            #         success, payload = remove_appointment_google(
            #             date,
            #             hour
            #         )
            #         prompt_result = (
            #             "Genera una respuesta corta y amigable para el usuario "
            #             "basada en el resultado de eliminar una cita.\n\n"
            #             f"success={success}\n"
            #             f"payload={json.dumps(payload, ensure_ascii=False)}"
            #         )
            #         ok, response_text = get_response_openai(prompt_result, data.prompt)
            #     else:
            #         logger.error("La herramienta solicitada no es válida.")
            #         response_text = get_message("tool_invalid", lang)
            # else:
            #     logger.error("No pude procesar la solicitud")
            #     response_text = get_message("technical_error", lang)

    except urllib.error.HTTPError as e:

        error_body = e.read().decode("utf-8")

        logger.error(
            f"OpenAI HTTP {e.code}: {error_body}"
        )

        error_json = json.loads(error_body)

        error_code = (
            error_json
            .get("error", {})
            .get("code")
        )

        if error_code == "billing_not_active":
            # TODO: Change model
            logger.error("La cuenta de OpenAI no tiene billing activo.")
        elif error_code == "invalid_api_key":
            logger.error("El apikey OpenAI es invalida.")
        else:
            logger.error("Hubo un problema con OpenAI.")

        response_text = get_message("technical_error", lang)
    except Exception as e:
        logger.error(f"Error OpenAI: {str(e)}")
        response_text = get_message("technical_error", lang)

    return response_text

def analyze_image_openai(data_image, prompt="", model="gpt-4.1-mini"):
    image_base64 = data_image.data
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1
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
            return result["choices"][0]["message"]

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"OpenAI HTTP Error: {e.code} - {error_body}")
        return "Error al analizar la imagen."

    except Exception as e:
        logger.error(f"OpenAI Error: {str(e)}")
        return "Error al analizar la imagen."