import os
import boto3

dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.environ.get(
        'AWS_REGION',
        'us-east-1'
    )
)

CHAT_HISTORY_TABLE = os.environ.get(
    'CHAT_HISTORY_TABLE',
    'ChatHistory'
)

chat_history_table = dynamodb.Table(
    CHAT_HISTORY_TABLE
)