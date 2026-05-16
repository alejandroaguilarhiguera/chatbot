import json
from shared.google_calendar import get_calendar_events_google


def lambda_handler(event, context):
    success, events = get_calendar_events_google()
    if success:
        return {
            "statusCode": 200,
            "body": json.dumps({"events": events })
        }
    else:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve calendar events"})
        }