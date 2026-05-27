
import json

def validate_message_data(data):
    if not data.message:
        return {
            "statusCode": 200,
            "body": json.dumps({"ignored": True})
        }

    if not data.phone_id:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "No se envio el ID del remitente"
            })
        }

    return None