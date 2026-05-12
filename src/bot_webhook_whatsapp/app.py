import os
import json
import urllib.request

from shared.ai_service import get_gemini_response


WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")

PHONE_NUMBER_ID = os.environ.get(
    "PHONE_NUMBER_ID"
)

WHATSAPP_URL = (
    f"https://graph.facebook.com/v23.0/"
    f"{PHONE_NUMBER_ID}/messages"
)


def lambda_handler(event, context):

    body = json.loads(event['body'])

    entry = body['entry'][0]

    changes = entry['changes'][0]

    value = changes['value']

    if 'messages' not in value:
        return {
            "statusCode": 200,
            "body": json.dumps({
                "ok": True
            })
        }

    message = value['messages'][0]

    phone = message['from']

    incoming_text = (
        message.get('text', {})
        .get('body', '')
    )

    if phone and incoming_text:

        ai_response = get_gemini_response(
            str(phone),
            incoming_text
        )

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "text": {
                "body": ai_response
            }
        }

        req = urllib.request.Request(
            WHATSAPP_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {WHATSAPP_TOKEN}"
            },
            method="POST"
        )

        urllib.request.urlopen(req)

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }