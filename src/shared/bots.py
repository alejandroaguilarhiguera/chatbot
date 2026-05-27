import os
import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
table_name = os.environ["BOTS_TABLE"]
table = dynamodb.Table(table_name)

def get_bot(bot_id: str):
    print("table_name>>>> "+str(table_name))
    response = table.get_item(
        Key={
            "bot_id": bot_id
        }
    )

    return response.get("Item")