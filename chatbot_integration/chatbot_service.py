import os
import requests
from dotenv import load_dotenv

load_dotenv()

# DEBUG info
print("=== CHATBOT SERVICE STARTED ===")

# Try both possible environment variable names
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_API_KEY")

if not HF_API_KEY:
    print("⚠️ WARNING: No Hugging Face API key found. Using fallback responses.")
else:
    print(f"✅ API Key loaded: {HF_API_KEY[:10]}...")

# Use a simpler, more available model
API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-small"
print(f"✅ Using model: {API_URL.split('/')[-1]}")

HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}" if HF_API_KEY else "",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """Tu esi e-veikala čatbots-asistents. Atbildi tikai uz jautājumiem par veikalu un precēm.
Preces: {products}
Ja jautājums nav par veikalu, atsaki pieklājīgi.
Atbildi latviešu valodā, īsi un skaidri."""


def get_chatbot_response(message, history, products=None):
    """
    message: lietotāja ievade (string)
    history: sarunas vēsture (list)
    products: produktu saraksts (optional)
    """
    
    # If no API key, use fallback
    if not HF_API_KEY:
        return get_fallback_response(message, products)
    
    # Format products text
    product_text = ""
    if products and len(products) > 0:
        product_text = "Pieejamās preces:\n"
        for p in products:
            product_text += f"- {p['name']} (€{p['price']:.2f})\n"
    else:
        product_text = "Šobrīd nav pieejamu produktu."
    
    # Create prompt
    prompt = SYSTEM_PROMPT.format(products=product_text)
    
    # Add conversation history
    if history and len(history) > 0:
        prompt += "\n\nSarunas vēsture:\n"
        for msg in history[-3:]:  # Last 3 messages only
            role = "Lietotājs" if msg.get("role") == "user" else "Asistents"
            prompt += f"{role}: {msg.get('content', '')}\n"
    
    prompt += f"\nLietotājs: {message}\nAsistents:"
    
    # Prepare payload for DialoGPT
    payload = {
        "inputs": {
            "text": prompt
        },
        "parameters": {
            "max_length": 100,
            "temperature": 0.7
        }
    }
    
    try:
        print(f"🤖 Sending request to Hugging Face API...")
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        
        print(f"📡 API Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📦 API Response data: {data}")
            
            # DialoGPT returns different format
            if isinstance(data, list) and len(data) > 0:
                if "generated_text" in data[0]:
                    return data[0]["generated_text"]
                elif "text" in data[0]:
                    return data[0]["text"]
            elif "generated_text" in data:
                return data["generated_text"]
            else:
                return get_fallback_response(message, products)
        else:
            print(f"❌ API Error {response.status_code}: {response.text[:200]}")
            return get_fallback_response(message, products)
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return get_fallback_response(message, products)


def get_fallback_response(message, products):
    """Fallback responses when API fails"""
    message_lower = message.lower()
    
    # Check for product-related questions
    product_keywords = ["produkt", "prece", "kādi", "kas", "cena", "cik maksā"]
    if any(keyword in message_lower for keyword in product_keywords):
        if products and len(products) > 0:
            response = "Mūsu veikalā pieejamas šādas preces:\n"
            for p in products[:3]:  # Show first 3 products
                response += f"- {p['name']} (€{p['price']:.2f})\n"
            response += "\nVai vēlaties uzzināt vairāk par kādu konkrētu produktu?"
            return response
        else:
            return "Šobrīd nav pieejamu produktu. Lūdzu, vēlāk mēģiniet vēlreiz."
    
    # Default response
    return "Es varu palīdzēt ar informāciju par veikala produktiem. Vai vēlaties uzzināt, kādi produkti ir pieejami?"