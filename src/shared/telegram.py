import os
import json
import urllib.request
import urllib.parse
from dataclasses import dataclass
import base64
import mimetypes


TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
channel = 'telegram'


@dataclass
class ImageData:
    content_type: str
    data: str
    url: str


@dataclass
class TelegramEventData:
    message: str
    from_: str
    to: str
    phone_id: str
    lang: str
    channel: str
    file_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    prompt: str | None = None


def get_data_from_event(event) -> TelegramEventData:
    body = json.loads(event["body"])

    message_data = body.get("message", {})
    user = message_data.get("from", {})

    phone_id = str(message_data.get("chat", {}).get("id"))
    message = message_data.get("text", "")
    
    lang = user.get("language_code", "es")

    photos = message_data.get("photo")
    file_id = photos[-1]["file_id"] if photos else None

    return TelegramEventData(
        message=message,
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        from_=phone_id,
        to=TELEGRAM_URL,
        phone_id=phone_id,
        lang=lang,
        channel=channel,
        file_id=file_id,
    )


def send_message(to: str, phone_id: str, ai_response: str):
    data = urllib.parse.urlencode({
        'channel': channel,
        'chat_id': phone_id,
        'text': ai_response
    }).encode('utf-8')

    req = urllib.request.Request(to, data=data)
    urllib.request.urlopen(req)


def get_image(file_id: str) -> ImageData:
    # 1. Obtener el file_path
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={urllib.parse.quote(file_id)}"
    with urllib.request.urlopen(url) as r:
        file_path = json.loads(r.read())["result"]["file_path"]

    # 2. Descargar los bytes de la imagen
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    with urllib.request.urlopen(file_url) as r:
        image_bytes = r.read()

    # 3. Detectar content_type y convertir a base64
    content_type, _ = mimetypes.guess_type(file_path)

    return ImageData(
        content_type=content_type or "image/jpeg",
        data=base64.b64encode(image_bytes).decode("utf-8"),
        url=file_url
    )