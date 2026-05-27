from shared.openai import call_openai
from shared.gemini import call_gemini
from shared.groq import call_groq


def get_ai_response(
    model_ai: str,
    channel: str,
    phone_id: str,
    message: str
):
    if model_ai == "gemini":
        return call_gemini(
            channel,
            phone_id,
            message
        )

    if model_ai == "openai":
        return call_openai(
            channel,
            phone_id,
            message
        )

    return call_groq(
        channel,
        phone_id,
        message
    )