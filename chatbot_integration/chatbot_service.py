import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

# OBLIGĀTI izmantot šo modeli
API_URL = "https://api-inference.huggingface.co/models/katanemo/Arch-Router-1.5B"
print(f"✅ Using REQUIRED model: katanemo/Arch-Router-1.5B")

HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_API_KEY")

if not HF_API_KEY:
    print("⚠️ WARNING: No Hugging Face API key. Using simulated responses.")
    SIMULATED_MODE = True
else:
    print(f"✅ API Key loaded")
    SIMULATED_MODE = False

HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}" if HF_API_KEY else "",
    "Content-Type": "application/json"
}

def should_block_response(user_message):
    """Čatbota uzvedības kontrole - tikai e-veikala temati"""
    shop_keywords = [
        "produkt", "prece", "cena", "pasūtīt", "grozs", "apmaksāt", 
        "piegāde", "atgriešana", "veikals", "iegādāties", "noliktava",
        "kādi", "kas", "cik", "kā", "palīdzība", "palīdzēt"
    ]
    
    message_lower = user_message.lower()
    
    # Pārbauda vai ir e-veikala atslēgvārdi
    for keyword in shop_keywords:
        if keyword in message_lower:
            return False  # Atļaut - ir par veikalu
    
    return True  # Bloķēt - nav par veikalu

def get_chatbot_response(message, history, products=None):
    """
    Implementācija ar OBLIGĀTO modeli katanemo/Arch-Router-1.5B
    """
    
    # 1. ČATBOTA UZVEDĪBAS KONTROLE
    if should_block_response(message):
        return "Atvainojiet, es varu atbildēt tikai uz jautājumiem, kas saistīti ar mūsu e-veikalu un tā precēm. Vai varu palīdzēt ar kaut ko citu saistībā ar mūsu produktiem vai pasūtījumiem?"
    
    # 2. FORMATĒT PRODUKTUS
    product_text = ""
    if products and len(products) > 0:
        product_text = "\n\nPieejamās preces šobrīd:\n"
        for p in products:
            product_text += f"- {p['name']} (€{p['price']:.2f})\n"
    else:
        product_text = "\n\nŠobrīd nav pieejamu produktu."
    
    # 3. SISTĒMAS INSTRUKCIJA (e-veikala asistents)
    system_prompt = f"""Tu esi e-veikala čatbots-asistents. Atbildi tikai uz jautājumiem par veikalu un precēm.
    
    Svarīgi norādījumi:
    1. Atbildi tikai latviešu valodā
    2. Atbildi īsi un skaldi
    3. Koncentrējies tikai uz veikala tematiem
    4. Ja nezini atbildi, pateici, ka vari palīdzēt tikai ar veikala jautājumiem
    5. Būt draudzīgs un profesionāls
    {product_text}
    """
    
    # 4. JA NAV API ATSLĒGAS, IZMANTO SIMULĒTAS ATBILDES
    if SIMULATED_MODE or not HF_API_KEY:
        return get_simulated_response(message, products)
    
    # 5. SAGAIDĀMĀ ATBILDE NO Arch-Router-1.5B
    try:
        # Formatēt vēsturi
        formatted_history = ""
        if history and len(history) > 0:
            for msg in history[-4:]:  # Pēdējās 4 ziņas
                role = "Lietotājs" if msg.get("role") == "user" else "Asistents"
                formatted_history += f"{role}: {msg.get('content', '')}\n"
        
        # Pilnais prompt
        full_prompt = f"""{system_prompt}
        
        Sarunas vēsture:
        {formatted_history}
        
        Lietotājs: {message}
        
        Asistents:"""
        
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        print(f"🚀 Sending to Arch-Router-1.5B: '{message[:50]}...'")
        
        # Iesniegt pieprasījumu
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=45)
        
        print(f"📡 API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Parsēt Arch-Router atbildi
            if isinstance(data, list) and len(data) > 0:
                if "generated_text" in data[0]:
                    return data[0]["generated_text"].strip()
                else:
                    return get_simulated_response(message, products)
            else:
                return get_simulated_response(message, products)
        
        elif response.status_code == 503:
            # Modelis ielādējas
            return "Modelis šobrīd ielādējas. Šī ir simulēta atbilde: " + get_simulated_response(message, products)
        
        else:
            print(f"❌ API Error: {response.status_code} - {response.text[:200]}")
            return get_simulated_response(message, products)
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return get_simulated_response(message, products)

def get_simulated_response(message, products):
    """Simulētas atbildes, ja API nestrādā - BET pēc Arch-Router stila"""
    message_lower = message.lower()
    
    # Simulētas atbildes Arch-Router stilā
    if any(word in message_lower for word in ["kādi", "produkti", "preces", "kas ir", "pieejami"]):
        if products and len(products) > 0:
            response = "Pamatojoties uz pieejamo produktu sarakstu, es varu pateikt:\n\n"
            for p in products[:4]:
                response += f"• {p['name']} - €{p['price']:.2f}\n"
            response += "\nVai vēlaties uzzināt vairāk par kādu konkrētu produktu?"
            return response
        else:
            return "Pašlaik nav pieejamu produktu. Lūdzu, pārbaudiet vēlāk."
    
    elif any(word in message_lower for word in ["cena", "cik maksā", "cik maksā"]):
        return "Produktu cenas variē no €349.99 līdz €1999.99. Kuru produkta cenu vēlaties uzzināt precīzāk?"
    
    elif "palīdzība" in message_lower or "palīdzēt" in message_lower:
        return "Es varu palīdzēt ar:\n1. Produktu informāciju\n2. Cenu pārbaudi\n3. Pasūtījumu procesu\n\nAr ko konkrēti varu palīdzēt?"
    
    elif any(word in message_lower for word in ["paldies", "labs", "super"]):
        return "Prieks palīdzēt! Vai ir vēl kāds jautājums par mūsu veikalu?"
    
    else:
        # Ja nav atpazīts, bet ir par veikalu
        if not should_block_response(message):
            return "Es varu atbildēt uz jautājumiem par mūsu produktiem, cenām un pasūtījumu procesu. Vai vēlaties uzzināt kaut ko konkrētu?"
        else:
            return "Atvainojiet, esmu programmēts palīdzēt tikai ar jautājumiem saistībā ar mūsu e-veikalu."