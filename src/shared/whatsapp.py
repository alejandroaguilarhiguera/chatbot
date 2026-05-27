
import os
from twilio.rest import Client
from urllib.parse import parse_qs

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)

def get_data_from_event(event):
    body = event.get('body', '')
    if event.get('isBase64Encoded', False):
        import base64
        body = base64.b64decode(body).decode('utf-8')
    params = parse_qs(body)

    message = params.get('Body', [''])[0]
    from_number = params.get('From', [''])[0]
    to = params.get('To', [''])[0]
    phone_id = params.get('WaId', [''])[0]
    return message, from_number, to, phone_id

def send_message(from_number: str, to: str, message: str):
    # Placeholder function to send a WhatsApp message
    message = client.messages.create(
      body=message,
      from_=to,
      to=from_number
    )

