import os
import json
import urllib.request
import urllib.parse

# from shared.openai import call_openai
# from shared.gemini import call_gemini
from shared.groq import call_groq

TOKEN = os.environ.get("TELEGRAM_TOKEN")

TELEGRAM_URL = (
    f"https://api.telegram.org/bot{TOKEN}/sendMessage"
)

def lambda_handler(event, context):

    body = json.loads(event['body'])

    message = body.get('message', {})

    chat_id = message.get('chat', {}).get('id')

    incoming_text = message.get('text', '')

    if chat_id and incoming_text:

        ai_response = call_groq(
            str(chat_id),
            incoming_text
        )

        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': ai_response
        }).encode('utf-8')

        req = urllib.request.Request(
            TELEGRAM_URL,
            data=data
        )

        urllib.request.urlopen(req)

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }