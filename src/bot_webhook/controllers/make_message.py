import json
from types import SimpleNamespace
from shared.contact import upsert_contact
from shared.bots import get_bot
from shared.history_service import save_message
from shared.google_calendar import (
    book_appointment_google,
    remove_appointment_google,
    get_calendar_events_google
)
from shared.openai import get_response_openai
from shared.messages import get_message
from shared.ai import get_ai_response, analyze_image
from shared.telegram import send_message as telegram_send_message, get_image as get_telegram_image
from shared.whatsapp import send_message as whatsapp_send_message, get_image as get_whatsapp_image
import logging

logger = logging.getLogger()


CHANNEL_REGISTRY = {
    "telegram": {
        "send_message": telegram_send_message,
        "get_image": get_telegram_image,
    },
    "whatsapp": {
        "send_message": whatsapp_send_message,
        "get_image": get_whatsapp_image,
    },
}
def make_message_handler(event, context):
    data = SimpleNamespace(**event)
    channel_config = CHANNEL_REGISTRY.get(data.channel)
    if not channel_config:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Canal no soportado"})
        }
    bot = get_bot(data.phone_id)
    if not bot:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No se encontro un bot para este contacto"})
        }
    default_contact = {
        "phone": data.phone_id,
        "lang": data.lang,
        "channel": data.channel,
        "model_ai": 'groq'
    }
    contact = upsert_contact(default_contact, bot["tenant"])
    send_message = channel_config["send_message"]
    if data.file_id:
        get_image = channel_config.get("get_image")
        file = get_image(data.file_id)
        parsed_response = None

        # "data:image/jpeg;base64,"+ str(file.data)
        data.file = file
        ai_response = analyze_image(file)
        try:
            parsed_response = json.loads(ai_response)
            if (parsed_response.get("amount") > 0):
                # TODO: Translate
                response_text = "Confirmo que he recibido el pago."
                save_message(data.channel, data.phone_id, 'assistant', response_text)

            else:
                # TODO: Translate
                response_text = "No pude extraer un monto válido del recibo. Asegúrate de que el recibo sea claro y legible."
                logger.error(response_text)
                save_message(data.channel, data.phone_id, 'assistant', response_text)

            
        except json.JSONDecodeError:
            response_text = "No pude analizar la imagen. Prueba con otra imagen o asegúrate de que el recibo sea claro y legible."
            logger.error(response_text)
            save_message(data.channel, data.phone_id, 'assistant', response_text)
        
        send_message(data.to, data.phone_id, response_text)

        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True})
        }

    else:
        ai_response = get_ai_response(
            data=data,
            bot=bot,
            contact=contact
        )
    
    # Proceso de validar y agendar


    response_text = ai_response.get("content", "")
    message = ai_response

    if message.get("tool_calls"):
        lang = contact.get("lang", "es")
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

                ok, response_text = get_response_openai(prompt_result, data.prompt)

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
                ok, response_text = get_response_openai(prompt_result, data.prompt)

            else:
                logger.error("Hubo un error al intentar agendar la cita.")
                response_text = get_message("error_book", lang)

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
            ok, response_text = get_response_openai(prompt_result, data.prompt)
        else:
            logger.error("La herramienta solicitada no es válida.")
            response_text = get_message("tool_invalid", lang)


    send_message(data.to, data.phone_id, response_text)

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }