import os
import json
from shared.validate_message import validate_message_data
from shared.contact import upsert_contact
from shared.openai import call_openai
from shared.gemini import call_gemini
from shared.groq import call_groq
from shared.bots import get_bot
from shared.telegram import get_data_from_event, send_message
from shared.ai import get_ai_response

TOKEN = os.environ.get("TELEGRAM_TOKEN")

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

channel = 'telegram'

def lambda_handler(event, context):
    data = get_data_from_event(event)
    to = data.to
    phone_id = data.phone_id
    lang = data.lang
    
    validation_error = validate_message_data(data)
    if validation_error:
        return validation_error
    
    bot = get_bot(phone_id)
    if not bot:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No se encontro un bot para este contacto"})
        }
    default_contact = {
        "phone": phone_id,
        "lang": lang,
        "channel": channel,
        "model_ai": 'groq'
    }
    contact = upsert_contact(default_contact, bot["tenant"])

    ai_response = get_ai_response(
        contact.get("model_ai", "groq"),
        channel,
        str(data.phone_id),
        data.message
    )

    send_message(to, phone_id, ai_response)

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }