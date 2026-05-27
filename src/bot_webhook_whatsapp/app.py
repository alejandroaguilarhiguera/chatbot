import os
from twilio.rest import Client
import json
from urllib.parse import parse_qs
from shared.contact import upsert_contact
from shared.openai import call_openai
from shared.gemini import call_gemini
from shared.groq import call_groq
from shared.bots import get_bot
from shared.whatsapp import get_data_from_event, send_message
from shared.validate_message import validate_message_data
from shared.ai import get_ai_response

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)
channel = 'whatsapp'

def lambda_handler(event, context):
    data = get_data_from_event(event)
    from_ = data.from_
    to = data.to
    phone_id = data.phone_id

    validation_error = validate_message_data(data)

    if validation_error:
        return validation_error

    if not phone_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No se envio el ID del remitente"})
        }
    bot = get_bot(phone_id)
    if not bot:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No se encontro un bot para este contacto"})
        }
    default_contact = {
        "phone": phone_id,
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
    send_message(from_, to, ai_response)
    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }