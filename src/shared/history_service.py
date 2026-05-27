from http import client
import os
from urllib import response
import boto3

from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table(os.environ.get('CHAT_HISTORY_TABLE'))

TTL_DAYS = int(os.environ.get('HISTORY_TTL_DAYS', 30))
client = boto3.client("dynamodb")


def save_message(channel: str, chat_id: str, role: str, text: str):
    now = datetime.now(timezone.utc)
    ttl = int((now + timedelta(days=TTL_DAYS)).timestamp())

    table.put_item(Item={
        'channel':   channel,
        'chat_id':   str(chat_id),
        'timestamp': now.isoformat(),
        'role':      role,
        'message':   text,
        'ttl':       ttl
    })

def get_history(chat_id: str, limit: int = 10) -> list:
    from boto3.dynamodb.conditions import Key
    response = table.query(
        KeyConditionExpression=Key('chat_id').eq(str(chat_id)),
        ScanIndexForward=False,
        Limit=limit
    )
    return list(reversed(response['Items']))
