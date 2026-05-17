
import os
import json
import base64
from datetime import datetime, timedelta
import zoneinfo
from google.oauth2 import service_account
from googleapiclient.discovery import build

CALENDAR_ID = os.environ.get("CALENDAR_ID", "")


def book_appointment_google(date, hour, reason):
    try:
        # Variable de entorno
        b64_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

        if not b64_json:
            return False, "GOOGLE_SERVICE_ACCOUNT_JSON no configurado"

        # Decodificar credenciales
        decoded_json = base64.b64decode(b64_json).decode('utf-8')
        service_account_info = json.loads(decoded_json)

        # Fix private_key
        if "private_key" in service_account_info:
            service_account_info["private_key"] = (
                service_account_info["private_key"]
                .replace("\\n", "\n")
            )

        # Scopes
        SCOPES = ['https://www.googleapis.com/auth/calendar']

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        # Cliente Google Calendar
        service = build(
            'calendar',
            'v3',
            credentials=credentials,
            cache_discovery=False
        )

        # Zona horaria
        local_tz = zoneinfo.ZoneInfo(
            os.environ.get('TZ', 'America/Mazatlan')
        )

        # Horario solicitado
        local_start = datetime.strptime(
            f"{date} {hour}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=local_tz)

        local_end = local_start + timedelta(hours=1)

        # Inicio y fin del día
        day_start = datetime.strptime(
            f"{date} 00:00",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=local_tz)

        day_end = day_start + timedelta(days=1)

        # Obtener eventos del día
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        # Validar conflictos
        for existing_event in events:

            existing_start_str = existing_event['start'].get('dateTime')
            existing_end_str = existing_event['end'].get('dateTime')

            # Ignorar eventos sin horario exacto
            if not existing_start_str or not existing_end_str:
                continue

            existing_start = datetime.fromisoformat(
                existing_start_str
            )

            existing_end = datetime.fromisoformat(
                existing_end_str
            )

            # Detectar traslape
            overlap = (
                local_start < existing_end and
                local_end > existing_start
            )

            if overlap:
                return (
                    False,
                    {
                        "message": "Horario no disponible",
                        "code": "SLOT_OCCUPIED",
                    }
                )

        # Crear evento
        event = {
            'summary': reason,
            'description': 'Agendado por Chatbot',
            'start': {
                'dateTime': local_start.isoformat(),
                'timeZone': 'America/Mazatlan',
            },
            'end': {
                'dateTime': local_end.isoformat(),
                'timeZone': 'America/Mazatlan',
            },
        }

        created_event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()

        return True, {
            "message": "Cita agendada correctamente",
            "event_id": created_event.get("id"),
            "event_link": created_event.get("htmlLink"),
            "start": local_start.isoformat(),
            "end": local_end.isoformat()
        }

    except Exception as e:
        print(f"Error en Google Calendar: {str(e)}")
        return False, { "message": str(e), "code": "GOOGLE_CALENDAR_ERROR" }
