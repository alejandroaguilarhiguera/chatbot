import os
from twilio.rest import Client
import json
from urllib.parse import parse_qs
from shared.openai import call_openai

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)
channel = 'whatsapp'

def lambda_handler(event, context):
    body = event.get('body', '')
    
    if event.get('isBase64Encoded', False):
        import base64
        body = base64.b64decode(body).decode('utf-8')
    
    params = parse_qs(body)

    message = params.get('Body', [''])[0]
    from_number = params.get('From', [''])[0]
    to = params.get('To', [''])[0]
    wa_id = params.get('WaId', [''])[0]
    
    ai_response = call_openai(
        channel,
        str(wa_id),
        message
    )

    message = client.messages.create(
      body=ai_response,
      from_=to,
      to=from_number
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }