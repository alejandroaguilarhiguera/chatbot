from shared.openai import call_openai
from shared.gemini import call_gemini
from shared.groq import call_groq


def get_ai_response(data, bot, contact):
    model_ai = contact.get("model_ai", "groq")
    data.prompt = bot["prompt"]
    data.chat_id = contact.get("chat_id")
    if model_ai == "gemini":
        return call_gemini(data)
    if model_ai == "openai":
        return call_openai(data)
    return call_groq(data)