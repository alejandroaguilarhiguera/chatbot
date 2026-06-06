import os
import base64
from typing import TypedDict
from dataclasses import dataclass
from urllib.parse import parse_qs

from twilio.rest import Client

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)
channel = 'whatsapp'

@dataclass
class WhatsappEventData:
    message: str
    # img: str | None
    first_name: str | None
    last_name: str | None
    from_: str
    to: str
    phone_id: str
    lang: str | None
    channel: str
    prompt: str | None = None


def get_data_from_event(event) -> WhatsappEventData:
    body = event.get("body", "")
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body).decode("utf-8")
    params = parse_qs(body)
    message = params.get("Body", [""])[0]
    from_number = params.get("From", [""])[0]
    to = params.get("To", [""])[0]
    phone_id = params.get("WaId", [""])[0]
    # num_media = int(event.get("NumMedia", 0))

    profile_name = params.get("ProfileName", [""])[0]

    first_name = None
    last_name = None

    if profile_name:
        parts = profile_name.split(" ", 1)
        first_name = parts[0]

        if len(parts) > 1:
            last_name = parts[1]

    return WhatsappEventData(
        message=message,
        first_name=first_name,
        last_name=last_name,
        from_=from_number,
        to=to,
        # img=ImageData(url=event["MediaUrl0"], content_type=event["MediaContentType0"]) if num_media > 0 else None,
        phone_id=phone_id,
        lang=None,
        channel=channel,
    )


def send_message(to:str, from_: str, message: str):
    client.messages.create(
        body=message,
        from_=to,
        to=from_
    )


def get_image(file_id: str):
    # TODO: implementar función para obtener imagen de whatsapp
    pass