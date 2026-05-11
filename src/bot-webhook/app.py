import os
import json
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # 1. Obtener el token de las variables de entorno
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    try:
        if 'body' in event:
            # Parsear el webhook de Telegram
            telegram_data = json.loads(event['body'])
            message = telegram_data.get('message', {})
            
            chat_id = message.get('chat', {}).get('id')
            incoming_text = message.get('text', '')

            if chat_id and incoming_text:
                # 2. Preparar el mensaje de respuesta
                reply_text = f"{incoming_text} prueba desde lambda"
                
                # 3. Configurar los datos para el POST (form url encoded)
                data = urllib.parse.urlencode({
                    'chat_id': chat_id,
                    'text': reply_text
                }).encode('utf-8')
                
                # 4. Enviar la petición a Telegram
                req = urllib.request.Request(TELEGRAM_URL, data=data)
                with urllib.request.urlopen(req) as response:
                    res_body = response.read().decode('utf-8')
                    logger.info(f"Respuesta de Telegram: {res_body}")

            response_body = {
                "status": "Mensaje procesado",
                "chat_id": chat_id
            }
        else:
            response_body = {"message": "No se encontró contenido en el cuerpo."}
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        response_body = {"error": str(e)}

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }