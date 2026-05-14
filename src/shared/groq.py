import os
import json
import urllib.request
import logging
from datetime import datetime

from shared.history_service import save_message, get_history
from shared.prompts import rules
from shared.google_calendar import book_appointment_google, remove_appointment_google

logger = logging.getLogger()

def call_groq(chat_id: str, user_message: str, model="llama-3.3-70b-versatile"):
    # 1. Historial
    save_message(chat_id, 'user', user_message)
    history = get_history(chat_id, limit=10)
    
    messages = [
        {"role": msg['role'], "content": msg['message']}
        for msg in history
    ]
    
    # 2. Contexto Temporal (Asumiendo TZ="America/Mazatlan" en template.yaml)
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    dia_semana = now.strftime("%A")

    # Inyectamos el sistema con máxima prioridad
    system_message = (
        f"{rules}\n\n"
        f"INSTRUCCIONES DE HERRAMIENTAS:\n"
        f"- Usa 'book_appointment' para crear citas.\n"
        f"- Usa 'remove_book_appointment' para eliminar citas."
    )
    
    messages.insert(0, {"role": "system", "content": system_message})

    # 3. Herramientas (Nombres en español para mayor consistencia con el razonamiento)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Agenda una cita en el calendario de Google.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {"type": "string", "description": "Formato YYYY-MM-DD"},
                        "hora": {"type": "string", "description": "Formato HH:mm"},
                        "motivo": {"type": "string", "description": "Descripción breve"}
                    },
                    "required": ["fecha", "hora", "motivo"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "remove_book_appointment",
                "description": "Elimina una cita existente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {"type": "string", "description": "Formato YYYY-MM-DD"},
                        "hora": {"type": "string", "description": "Formato HH:mm"}
                    },
                    "required": ["fecha", "hora"]
                }
            }
        }
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "tools": tools,
        "tool_choice": "auto"
    }

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
        "User-Agent": "MyCustomBot/1.0"
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            message = result['choices'][0]['message']

            if 'tool_calls' in message:
                tool_call = message['tool_calls'][0]
                function_name = tool_call['function']['name']
                args = json.loads(tool_call['function']['arguments'])
                
                # Extraemos usando los nuevos nombres de parámetros
                fecha = args.get('fecha')
                hora = args.get('hora')
                motivo = args.get('motivo', 'Cita por Chatbot')

                if function_name == "book_appointment":
                    exito, detalle = book_appointment_google(fecha, hora, motivo)
                    response_text = (f"✅ ¡Perfecto! Tu cita ha sido agendada para el {fecha} a las {hora}." 
                                     if exito else f"❌ Error al agendar: {detalle}")
                
                elif function_name == "remove_book_appointment":
                    exito, detalle = remove_appointment_google(fecha, hora)
                    response_text = (f"🗑️ He eliminado tu cita del día {fecha} a las {hora}." 
                                     if exito else f"❌ No pude eliminar la cita: {detalle}")
                else:
                    response_text = "Lo siento, la acción solicitada no es válida."
            else:
                response_text = message.get('content', "No entiendo tu solicitud.")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Groq HTTP {e.code}: {error_body}")
        response_text = "Hubo un problema con el servicio de inteligencia artificial."
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        response_text = "Tengo problemas técnicos para procesar tu solicitud."

    save_message(chat_id, 'assistant', response_text)
    return response_text