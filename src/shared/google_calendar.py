import os
import json
import base64
from datetime import datetime, timedelta
import zoneinfo
from google.oauth2 import service_account
from googleapiclient.discovery import build

calendar_id = "alejandro.aguilar.higuera@gmail.com"

def get_calendar_events_google():
    date_now = datetime.now().strftime("%Y-%m-%d")
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

        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        # Cliente Google Calendar
        service = build(
            'calendar',
            'v3',
            credentials=creds
        )

        # Zona horaria local
        local_tz = zoneinfo.ZoneInfo(
            'America/Mazatlan'
        )

        # Fecha/hora LOCAL inicio y fin del día
        local_start = datetime.strptime(
            f"{date_now} 00:00",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=local_tz)

        local_end = local_start + timedelta(days=1)

        events_result = service.events().list(
            calendarId=calendar_id,
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
            calendarId=calendar_id,
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
            calendarId=calendar_id,
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

def remove_appointment_google(date, hour):
    """
    Busca una cita por fecha y hora exacta para obtener su ID y eliminarla.
    """
    try:
        # 1. Credenciales y Conexión (Igual que en agendar)
        b64_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not b64_json:
            return False, "Configuración de credenciales no encontrada."

        decoded_json = base64.b64decode(b64_json).decode('utf-8')
        service_account_info = json.loads(decoded_json)
        
        if "private_key" in service_account_info:
            service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES)
        
        service = build('calendar', 'v3', credentials=creds)

        # 2. Configurar el rango de búsqueda
        # Buscamos eventos que comiencen exactamente en la fecha y hora proporcionada
        # Usamos el offset -07:00 para la zona horaria de México
        time_search = f"{date}T{hour}:00-07:00"

        # 3. Listar eventos en ese horario específico
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_search,
            maxResults=5, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        if not events:
            return False, {"message": f"No se encontró ninguna cita el {date} a las {hour}.", "code": "APPOINTMENT_NOT_FOUND"}

        # 4. Filtrar para encontrar la coincidencia exacta de hora de inicio
        # (list() puede devolver eventos que empiezan después de timeMin)
        target_event = None
        for event in events:
            if event['start'].get('dateTime', '').startswith(f"{date}T{hour}"):
                target_event = event
                break

        if not target_event:
            return False, {"message":"No existe una cita que coincida exactamente con ese horario.", "code": "APPOINTMENT_NOT_FOUND"}

        # 5. Ejecutar la eliminación
        service.events().delete(
            calendarId=calendar_id, 
            eventId=target_event['id']
        ).execute()
        
        return True, {"message": "Cita eliminada correctamente."}

    except Exception as e:
        print(f"Error al eliminar en Google Calendar: {str(e)}")
        return False, {"message": str(e)}