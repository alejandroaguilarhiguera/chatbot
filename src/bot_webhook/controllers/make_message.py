import json
from types import SimpleNamespace
from shared.contact import upsert_contact
from shared.bots import get_bot
from shared.ai import get_ai_response
from shared.telegram import send_message as telegram_send_message
from shared.whatsapp import send_message as whatsapp_send_message

CHANNEL_REGISTRY = {
    "telegram": {
        "send_message": telegram_send_message,
    },
    "whatsapp": {
        "send_message": whatsapp_send_message,
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

    ai_response = get_ai_response(
        data=data,
        bot=bot,
        contact=contact
    )
    send_message = channel_config["send_message"]
    send_message(data.to, data.phone_id, ai_response)

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }