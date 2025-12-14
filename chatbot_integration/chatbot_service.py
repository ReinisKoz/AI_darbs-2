import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")

API_URL = "https://api-inference.huggingface.co/models/katanemo/Arch-Router-1.5B"
HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """
Tu esi e-veikala čatbots-asistents.
Tu atbildi tikai uz jautājumiem, kas saistīti ar šo e-veikalu un tā precēm.
Ja jautājums nav par e-veikalu, pieklājīgi atsaki un paskaidro, ka vari palīdzēt tikai ar veikala jautājumiem.
Atbildi skaidri, īsi un latviešu valodā.
"""


def get_chatbot_response(message, history, products=None):
    """
    message: lietotāja ievade (string)
    history: sarunas vēsture (list)
    products: produktu saraksts (optional)
    """

    # Ja API atslēga nav ielādēta
    if not HF_API_KEY:
        return "Kļūda: nav definēta Hugging Face API atslēga."

    # Saīsina vēsturi – samazina liekus API tokenus
    recent_history = history[-5:] if len(history) > 5 else history

    # Formatē vēsturi uz tekstu
    formatted_history = ""
    for msg in recent_history:
        role = "Lietotājs" if msg["role"] == "user" else "Asistents"
        formatted_history += f"{role}: {msg['content']}\n"

    # Ja ir preces — pievieno promptam
    product_text = ""
    if products:
        product_text = "\nPieejamās preces:\n"
        for p in products:
            product_text += f"- {p['name']} (€{p['price']})\n"

    full_prompt = f"""
{SYSTEM_PROMPT}

{product_text}

Sarunas vēsture:
{formatted_history}

Lietotāja jautājums:
{message}

Tava atbilde:
"""

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 150,
            "temperature": 0.6,
            "return_full_text": False
        }
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)

        if response.status_code != 200:
            return f"Kļūda no API: {response.status_code} – {response.text}"

        data = response.json()

        # HuggingFace parasti atgriež sarakstu
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "Nav atbildes.")
        elif "generated_text" in data:
            return data["generated_text"]
        else:
            return "Neizdevās iegūt atbildi no modeļa."

    except Exception as e:
        return f"Kļūda savienojumā ar MI: {str(e)}"
