from shared.history_service import save_message
import boto3, json, os

from shared.validate_message import validate_message_data
from shared.telegram import send_message as telegram_send_message
from shared.whatsapp import send_message as whatsapp_send_message

lambda_client = boto3.client("lambda")

CHANNEL_REGISTRY = {
    "telegram": {
        "send_message": telegram_send_message,
    },
    "whatsapp": {
        "send_message": whatsapp_send_message,
    },
}

def process_message(data):
    channel_config = CHANNEL_REGISTRY.get(data.channel)
    if not channel_config:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Canal no soportado"})
        }

    validation_error = validate_message_data(data)
    if validation_error:
        return validation_error
    
    save_message(
        data.channel,
        data.phone_id,
        "user",
        data.message,
    )
    is_local = os.environ.get("LOCAL", "false").lower() == "true"

    if is_local:
        from bot_webhook.controllers.make_message import make_message_handler
        make_message_handler(data.__dict__, context=None)
    else:
        lambda_client.invoke(
            FunctionName=os.environ["MAKE_MESSAGE_FUNCTION_NAME"],
            InvocationType="Event",
            Payload=json.dumps(data.__dict__)
        )


    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }