import logging
from shared.history_service import save_message, get_history
from shared.openai import call_openai, analyze_image_openai
from shared.gemini import call_gemini
from shared.groq import call_groq

logger = logging.getLogger()

def get_ai_response(data, bot, contact):
    model_ai = contact.get("model_ai", "groq")
    data.prompt = bot["prompt"]
    data.chat_id = contact.get("chat_id")
    save_message(data.channel, data.phone_id, 'user', data.message)
    message_history = get_history(data.phone_id, limit=10)
    messages = [
        {"role": msg['role'], "content": msg['message']}
        for msg in message_history
    ]
    messages.insert(0, {"role": "system", "content": bot["prompt"]})

    ai_response = None
    if model_ai == "gemini":
        ai_response = call_gemini(data, message_history)
    if model_ai == "openai":
        ai_response = call_openai(data, message_history)
    if model_ai == "groq":
        ai_response = call_groq(data, message_history)

    if ai_response is None:
        logger.error("No se pudo generar una respuesta de la AI")
        return None
    
    save_message(data.channel, data.phone_id, 'assistant', ai_response.get("content", ""))
    
    return ai_response

def analyze_image(image_file, model_ai="groq"):
    prompt = """
    
    Analiza esta imagen, debe ser un recibo de pago o una transferencia bancaria,
    extrae la información relevante y estructúrala en formato JSON.
    En caso de no ser un recibo o transferencia, responde con el JSON de ejemplo pero con los campos vacíos.
    Ejemplo de respuesta:
    {
      "operation_type": "",
      "operation_id": "",
      "datetime": "YYYY-MM-DDTHH:mm:ssZ",
      "concept": "",
      "amount": "",
      "source_account_last4": "",
      "beneficiary_name": "",
      "bank_name": "",
      "destination_account_last4": ""
    }
    """
    response = analyze_image_openai(image_file, prompt)

    return response