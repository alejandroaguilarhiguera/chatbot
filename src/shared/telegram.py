import os
import json
import urllib.request
import urllib.parse
from dataclasses import dataclass

TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
channel= 'telegram'

@dataclass
class TelegramEventData:
    message: str
    first_name: str | None
    last_name: str | None
    from_: str
    to: str
    phone_id: str
    lang: str
    channel: str
    prompt: str | None = None


def get_data_from_event(event) -> TelegramEventData:
    body = json.loads(event["body"])

    message_data = body.get("message", {})
    user = message_data.get("from", {})

    phone_id = str(message_data.get("chat", {}).get("id"))
    message = message_data.get("text", "")

    lang = user.get("language_code", "es")

    return TelegramEventData(
        message=message,
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        from_=phone_id,
        to=TELEGRAM_URL,
        phone_id=phone_id,
        lang=lang,
        channel=channel,
    )


def send_message(to: str, phone_id: str, ai_response: str):
    data = urllib.parse.urlencode({
        'channel': channel,
        'chat_id': phone_id,
        'text': ai_response
    }).encode('utf-8')

    req = urllib.request.Request(to, data=data)
    urllib.request.urlopen(req)