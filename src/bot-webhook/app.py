import os
import json
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_gemini_response(prompt):
    """Llamada a la API de Gemini usando urllib"""
    GEMINI_TOKEN = os.environ.get("GEMINI_TOKEN", "")
    # Usamos el modelo gemini-1.5-flash por ser rápido y económico
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_TOKEN}"    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            # Extraer el texto de la respuesta de Gemini
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"Error en Gemini API: {str(e)}")
        return "Lo siento, tuve un problema al procesar tu mensaje con la IA."

def lambda_handler(event, context):
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    try:
        if 'body' in event:
            telegram_data = json.loads(event['body'])
            message = telegram_data.get('message', {})
            
            chat_id = message.get('chat', {}).get('id')
            incoming_text = message.get('text', '')

            if chat_id and incoming_text:
                # 1. Obtener respuesta de la IA
                ai_response = get_gemini_response(incoming_text)

                data = urllib.parse.urlencode({
                    'chat_id': chat_id,
                    'text': ai_response
                }).encode('utf-8')
                
                req = urllib.request.Request(TELEGRAM_URL, data=data)
                with urllib.request.urlopen(req) as response:
                    logger.info(f"Telegram respondió: {response.read().decode('utf-8')}")

            response_body = {"status": "Mensaje procesado"}
        else:
            response_body = {"message": "No body found"}
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        response_body = {"error": str(e)}

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }