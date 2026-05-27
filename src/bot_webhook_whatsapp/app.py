import os
from twilio.rest import Client
import json
from urllib.parse import parse_qs
from shared.contact import upsert_contact
from shared.openai import call_openai
from shared.gemini import call_gemini
from shared.groq import call_groq
from shared.bots import get_bot
from whatsapp import get_data_from_event, send_message

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)
channel = 'whatsapp'

def lambda_handler(event, context):
    message, from_number, to, phone_id = get_data_from_event(event)

    if not message:
        return {
            "statusCode": 200,
            "body": json.dumps({"ignored": True})
        }
    if not phone_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No se envio el ID del remitente"})
        }
    default_contact = {
        "phone": phone_id,
        "channel": channel,
        "model_ai": 'groq'
    }

    bot = get_bot(phone_id)
    contact = upsert_contact(default_contact, bot["tenant"])

    if contact["model_ai"] == "gemini":
        ai_response = call_gemini(
            channel,
            str(phone_id),
            message
        )
    elif contact["model_ai"] == "openai":
        ai_response = call_openai(
            channel,
            str(phone_id),
            message
        )
    else:
        ai_response = call_groq(
            channel,
            str(phone_id),
            message
        )
    send_message(from_number, to, ai_response)
    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True, "response": (ai_response)})
    }