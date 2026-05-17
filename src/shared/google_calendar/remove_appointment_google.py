import os
import json
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build

CALENDAR_ID = os.environ.get("CALENDAR_ID", "")

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
            calendarId=CALENDAR_ID,
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
            calendarId=CALENDAR_ID,
            eventId=target_event['id']
        ).execute()
        
        return True, {"message": "Cita eliminada correctamente."}

    except Exception as e:
        print(f"Error al eliminar en Google Calendar: {str(e)}")
        return False, {"message": str(e)}