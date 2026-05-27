# shared/messages.py

MESSAGES = {
    "es": {
        "error_book":         "Hubo un error al intentar agendar la cita.",
        "tool_invalid":       "La herramienta solicitada no es válida.",
        "no_response":        "No pude procesar tu solicitud.",
        "billing_inactive":   "La cuenta de OpenAI no tiene billing activo.",
        "invalid_api_key":    "La API key de OpenAI es inválida.",
        "openai_error":       "Hubo un problema con OpenAI.",
        "technical_error":    "Tengo problemas técnicos para procesar tu solicitud.",
        "slot_occupied":      "La fecha {date} a las {hour} ya está ocupada.",
    },
    "en": {
        "error_book":         "There was an error trying to book the appointment.",
        "tool_invalid":       "The requested tool is not valid.",
        "no_response":        "I couldn't process your request.",
        "billing_inactive":   "The OpenAI account does not have active billing.",
        "invalid_api_key":    "The OpenAI API key is invalid.",
        "openai_error":       "There was a problem with OpenAI.",
        "technical_error":    "I'm having technical issues processing your request.",
        "slot_occupied":      "The slot on {date} at {hour} is already taken.",
    },
    "fr": {
        "error_book":         "Une erreur s'est produite lors de la prise de rendez-vous.",
        "tool_invalid":       "L'outil demandé n'est pas valide.",
        "no_response":        "Je n'ai pas pu traiter votre demande.",
        "billing_inactive":   "Le compte OpenAI n'a pas de facturation active.",
        "invalid_api_key":    "La clé API OpenAI est invalide.",
        "openai_error":       "Il y a eu un problème avec OpenAI.",
        "technical_error":    "J'ai des problèmes techniques pour traiter votre demande.",
        "slot_occupied":      "Le créneau du {date} à {hour} est déjà pris.",
    },
    "pt": {
        "error_book":         "Houve um erro ao tentar agendar a consulta.",
        "tool_invalid":       "A ferramenta solicitada não é válida.",
        "no_response":        "Não consegui processar sua solicitação.",
        "billing_inactive":   "A conta OpenAI não tem cobrança ativa.",
        "invalid_api_key":    "A chave de API do OpenAI é inválida.",
        "openai_error":       "Houve um problema com o OpenAI.",
        "technical_error":    "Estou com problemas técnicos para processar sua solicitação.",
        "slot_occupied":      "O horário em {date} às {hour} já está ocupado.",
    },
}

FALLBACK_LANG = "es"

def get_message(key: str, lang: str = FALLBACK_LANG, **kwargs) -> str:
    """
    Retorna el mensaje traducido para `key` en el idioma `lang`.
    Si el idioma no existe, usa el fallback.
    Acepta kwargs para formatear variables en el mensaje (e.g. date=, hour=).
    """
    lang = lang if lang in MESSAGES else FALLBACK_LANG
    text = MESSAGES[lang].get(key, MESSAGES[FALLBACK_LANG].get(key, key))
    return text.format(**kwargs) if kwargs else text
