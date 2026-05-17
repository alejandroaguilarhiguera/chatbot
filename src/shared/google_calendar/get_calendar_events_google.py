import os
import json
import base64
from datetime import datetime, timedelta
import zoneinfo
from google.oauth2 import service_account
from googleapiclient.discovery import build
CALENDAR_ID = os.environ.get("CALENDAR_ID", "")

def get_calendar_events_google(date):
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        # JSON Base64 de la cuenta de servicio
        b64_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

        if not b64_json:
            return False, "GOOGLE_SERVICE_ACCOUNT_JSON no configurado"

        # Decodificar JSON
        decoded_json = base64.b64decode(b64_json).decode('utf-8')
        service_account_info = json.loads(decoded_json)

        # Fix para saltos de línea de private_key
        if "private_key" in service_account_info:
            service_account_info["private_key"] = (
                service_account_info["private_key"]
                .replace("\\n", "\n")
            )

        # Scope Google Calendar
        SCOPES = ['https://www.googleapis.com/auth/calendar']

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        # Cliente Google Calendar
        service = build(
            'calendar',
            'v3',
            credentials=credentials
        )

        # Zona horaria local
        local_tz = zoneinfo.ZoneInfo(
            'America/Mazatlan'
        )

        # Fecha/hora LOCAL inicio y fin del día
        local_start = datetime.strptime(
            f"{date if date else date_now}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=local_tz)

        local_end = local_start + timedelta(days=1)

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=local_start.isoformat(),
            timeMax=local_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        return True, events

    except Exception as e:
        print(f"Error en Google Calendar: {str(e)}")
        return False, str(e)

