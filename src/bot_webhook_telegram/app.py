import os
import json
import urllib.request
import urllib.parse
from shared.contact import upsert_contact
from shared.openai import call_openai
from shared.gemini import call_gemini
from shared.groq import call_groq
from shared.bots import get_bot
from shared.telegram import get_data_from_event, send_message
import boto3

session = boto3.session.Session()

TOKEN = os.environ.get("TELEGRAM_TOKEN")

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

channel = 'telegram'

def lambda_handler(event, context):
    data = get_data_from_event(event)
    message = data.message
    to = data.to
    phone_id = data.phone_id
    lang = data.lang
    
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
        "lang": lang,
        "channel": channel,
        "model_ai": 'groq'
    }
    bot = get_bot(phone_id)
    if not bot:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No se encontro un bot para este contacto"})
        }
    contact = upsert_contact(default_contact, bot["tenant"])

    if bot["model_ai"] == "gemini":
        ai_response = call_gemini(
            channel,
            str(phone_id),
            message
        )
    elif bot["model_ai"] == "openai":
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

    send_message(to, phone_id, ai_response)

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }