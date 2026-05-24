# Integracion con telegram


## Paso 1 registrarse en BotFather


## Paso 2 configurar un webhook
Crear una funcion lambda con una url publica


Para configurar el webhook que recibe mensajes el bot:
https://api.telegram.org/bot<TOKEN>/setWebhook?url=<URL_API_GATEWAY>

* <TU_TOKEN>: El código que te dio BotFather.
* <URL_API_GATEWAY>: La URL que generó tu Lambda (debe empezar con https://).

Al recibir un mensaje desde telegram
```
{
    "update_id": 779125244,
    "message": {
      "message_id": 3,
      "from": {
        "id": 1576502097,
        "is_bot": false,
        "first_name": "Alejandro",
        "last_name": "Aguilar",
        "language_code": "es"
      },
      "chat": {
        "id": 1576502097,
        "first_name": "Alejandro",
        "last_name": "Aguilar",
        "type": "private"
      },
      "date": 1778379017,
      "text": "prueba 2"
    }
}
```



Para enviar un mensaje sera a la siguiente url:
https://api.telegram.org/bot<TOKEN>/sendMessage
form url encoded

key: chat_id
value: <number>

key: text
value: <string>




Al enviar un mensaje telegram el servidor responde lo siguiente:
```
{
  "ok": true,
  "result": {
    "message_id": 4,
    "from": {
      "id": 8293130970,
      "is_bot": true,
      "first_name": "Bfbot",
      "username": "blackfire113bot"
    },
    "chat": {
      "id": 1576502097,
      "first_name": "Alejandro",
      "last_name": "Aguilar",
      "type": "private"
    },
    "date": 1778379929,
    "text": "prueba 222 desde bruno"
  }
}
```


# Integracion con whatsapp(twilio)

## Registro de una cuenta en twilio
Conseguir lo siguiente:
* account_sid
* auth_token

# Integracion con OpenAI
# Integracion con Gemini
# Integracion con Groq
# Integracion con Google calendar