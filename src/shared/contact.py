import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
# table_name = os.environ["CONTACTS_TABLE"]
table_name = "Contacts-qa"
table = dynamodb.Table(table_name)

def upsert_contact(contact: dict, tenant_id: str):
    now = datetime.now(
        timezone.utc
    ).isoformat()

    response = table.update_item(
        Key={
            "tenant": tenant_id,
            "phone": contact["phone"]
        },

        UpdateExpression="""
            SET
                first_name = :first_name,
                last_name = :last_name,
                lang = :lang,
                channel = :channel,
                model_ai = :model_ai,
                updated_at = :updated_at,
                last_interaction_at = :last_interaction_at,
                created_at = if_not_exists(created_at, :created_at)
            ADD
                message_count :inc
        """,

        ExpressionAttributeValues={
            ":first_name": contact.get("first_name"),
            ":last_name": contact.get("last_name"),
            ":lang": contact.get("lang", "es"),
            ":channel": contact.get("channel"),
            ":model_ai": contact.get("model_ai"),
            ":updated_at": now,
            ":last_interaction_at": now,
            ":created_at": now,
            ":inc": 1
        },

        ReturnValues="ALL_NEW"
    )

    return response.get("Attributes")