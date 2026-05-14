import os
import json
import base64
from datetime import datetime, timedelta
import zoneinfo
from google.oauth2 import service_account
from googleapiclient.discovery import build

calendar_id = "alejandro.aguilar.higuera@gmail.com"

def book_appointment_google(fecha, hora, motivo):
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
            os.environ.get('TZ', 'America/Mazatlan')
        )

        # Fecha/hora LOCAL
        local_start = datetime.strptime(
            f"{fecha} {hora}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=local_tz)

        # Fin del evento
        local_end = local_start + timedelta(hours=1)

        # Evento
        event = {
            'summary': motivo,
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

        # Crear evento
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return True, created_event.get('htmlLink')

    except Exception as e:
        print(f"Error en Google Calendar: {str(e)}")
        return False, str(e)


def remove_appointment_google(fecha, hora):
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
        time_search = f"{fecha}T{hora}:00-07:00"

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
            return False, f"No se encontró ninguna cita el {fecha} a las {hora}."

        # 4. Filtrar para encontrar la coincidencia exacta de hora de inicio
        # (list() puede devolver eventos que empiezan después de timeMin)
        target_event = None
        for event in events:
            if event['start'].get('dateTime', '').startswith(f"{fecha}T{hora}"):
                target_event = event
                break

        if not target_event:
            return False, "No existe una cita que coincida exactamente con ese horario."

        # 5. Ejecutar la eliminación
        service.events().delete(
            calendarId=calendar_id, 
            eventId=target_event['id']
        ).execute()
        
        return True, "Cita eliminada correctamente."

    except Exception as e:
        print(f"Error al eliminar en Google Calendar: {str(e)}")
        return False, str(e)