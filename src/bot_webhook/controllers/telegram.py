from shared.telegram import get_data_from_event
from bot_webhook.controllers.messages_controller import process_message

def lambda_handler(event, context):
    data = get_data_from_event(event)
    return process_message(data)