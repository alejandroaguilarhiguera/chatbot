import json
from shared.bots import get_bot
from shared.contact import upsert_contact
from shared.ai import get_ai_response

# Adapta import según canal
from shared.telegram import send_message as tg_send
from shared.whatsapp import send_message as wa_send

def process_message(event, context):
    channel  = event["channel"]
    phone_id = event["phone_id"]

    bot = get_bot(phone_id)
    if not bot:
        return {"statusCode": 400, "body": "No bot found"}

    default_contact = {
        "phone":    phone_id,
        "channel":  channel,
        "model_ai": "groq",
        **({"lang": event["lang"]} if event.get("lang") else {}),
    }
    contact = upsert_contact(default_contact, bot["tenant"])

    # Reconstruye un objeto data mínimo que acepta get_ai_response
    class Data:
        pass
    data = Data()
    data.channel  = channel
    data.phone_id = phone_id
    data.message  = event["message"]
    data.to       = event.get("to")
    data.from_    = event.get("from_")
    data.lang     = event.get("lang")

    ai_response = get_ai_response(data=data, bot=bot, contact=contact)

    if channel == "telegram":
        tg_send(data.to, phone_id, ai_response)
    else:
        wa_send(data.from_, data.to, ai_response)

    return {"statusCode": 200, "body": json.dumps({"ok": True})}