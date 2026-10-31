from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestPayload(BaseModel):
    text: str
    target_lang: str = "mni-Mtei"

def simplify_english(text: str) -> str:
    cleaned = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?]) +', cleaned)
    short_text = " ".join(sentences[:2]) if len(sentences) > 1 else cleaned
    
    jargon_map = {
        "pursuant to": "under",
        "hereby requested to": "please",
        "shall be deemed": "is",
        "prior to": "before",
        "remittance": "payment",
        "beneficiary": "person receiving money",
        "mandatory": "required",
        "eligibility criteria": "rules to qualify",
        "disclaimer": "note",
        "information entered or displayed": "details shown",
        "based entirely on": "from",
        "solely responsible": "responsible"
    }
    
    simplified = short_text
    for jargon, simple in jargon_map.items():
        simplified = re.sub(re.escape(jargon), simple, simplified, flags=re.IGNORECASE)
        
    return simplified

def translate_to_meitei_mayek(text: str) -> str:
    word_dict = {
        "note": "ꯅꯣꯠ",
        "details": "ꯋꯥꯔꯦꯝ",
        "shown": "ꯎꯠꯂꯤꯕ",
        "information": "ꯄꯥꯎ",
        "user": "ꯁꯤꯖꯤꯟꯅꯔꯤꯕ ꯃꯤꯑꯣꯏ",
        "responsible": "ꯊꯧꯗꯥꯡ",
        "data": "ꯄꯥꯎ-ꯏ",
        "only": "ꯈꯛꯇꯅꯤ",
        "display": "ꯎꯠꯄ",
        "enter": "ꯍꯥꯞꯆꯤꯅꯕ",
        "please": "ꯆꯥꯟꯕꯤꯗꯨꯅ",
        "payment": "ꯁꯦꯜ ꯊꯤꯕ",
        "required": "ꯃꯊꯧ ꯇꯥꯕ"
    }
    
    char_map = {
        'a': 'ꯑ', 'b': 'ꯕ', 'c': 'ꯆ', 'd': 'ꯗ', 'e': 'ꯏ', 
        'f': 'ꯐ', 'g': 'ꯒ', 'h': 'ꯍ', 'i': 'ꯏ', 'j': 'ꯖ', 
        'k': 'ꯀ', 'l': 'ꯂ', 'm': 'ꯃ', 'n': 'ꯅ', 'o': 'ꯑꯣ', 
        'p': 'ꯄ', 'r': 'ꯔ', 's': 'ꯁ', 't': 'ꯇ', 'u': 'ꯨ', 
        'v': 'ꯚ', 'w': 'ꯋ', 'y': 'ꯌ', 'z': 'ꯖ'
    }
    
    words = text.split()
    translated_words = []
    for w in words:
        clean_w = re.sub(r'[^\w\s]', '', w.lower())
        if clean_w in word_dict:
            translated_words.append(word_dict[clean_w])
        else:
            meitei_chars = [char_map.get(ch.lower(), ch) for ch in w]
            translated_words.append("".join(meitei_chars))
            
    return " ".join(translated_words)

@app.post("/api/simplify")
async def simplify_and_translate(payload: RequestPayload):
    plain_english = simplify_english(payload.text)
    meitei_script = translate_to_meitei_mayek(plain_english)
    
    return {
        "status": "success",
        "engine": "Meitei Mayek Core Engine",
        "original_text": payload.text,
        "simplified_english": plain_english,
        "translated_text": meitei_script,
        "speak_text": plain_english
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
