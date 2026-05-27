import os
import json
from shared.validate_message import validate_message_data
from shared.contact import upsert_contact
from shared.bots import get_bot
from shared.ai import get_ai_response
from shared.telegram import get_data_from_event, send_message

def lambda_handler(event, context):
    data = get_data_from_event(event)
    validation_error = validate_message_data(data)
    if validation_error:
        return validation_error
    
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

    ai_response = get_ai_response(
        data=data,
        bot=bot,
        contact=contact
    )

    send_message(data.to, data.phone_id, ai_response)

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }