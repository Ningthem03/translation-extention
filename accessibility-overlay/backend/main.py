from functools import lru_cache
from threading import Lock
from io import BytesIO
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

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


_MODEL_ID = "naklitechie/indictrans2-en-indic-dist-200M"
_TTS_MODEL_ID = "naklitechie/indic-parler-tts"
_DEVICE_LOCK = Lock()
_TTS_LOCK = Lock()


@lru_cache(maxsize=1)
def get_translator():
    """Load IndicTrans2 once, on the first translation request."""
    import torch
    from IndicTransToolkit import IndicProcessor
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_ID, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        _MODEL_ID,
        trust_remote_code=True,
    ).to(device)
    model.eval()
    return torch, tokenizer, model, IndicProcessor(inference=True), device


@lru_cache(maxsize=1)
def get_speech_model():
    """Load the Manipuri speech model only when audio is requested."""
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer, GenerationConfig

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ParlerTTSForConditionalGeneration.from_pretrained(_TTS_MODEL_ID).to(device)
    if model.generation_config is None:
        model.generation_config = GenerationConfig.from_model_config(model.config)
    model.eval()
    prompt_tokenizer = AutoTokenizer.from_pretrained(_TTS_MODEL_ID)
    description_tokenizer = AutoTokenizer.from_pretrained(
        model.config.text_encoder._name_or_path
    )
    return torch, model, prompt_tokenizer, description_tokenizer, device


def simplify_english(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
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
        "solely responsible": "responsible",
    }
    for jargon, simple in jargon_map.items():
        cleaned = re.sub(re.escape(jargon), simple, cleaned, flags=re.IGNORECASE)
    return cleaned


def split_for_model(text: str, max_words: int = 100) -> list[str]:
    """Split long selections into sentence-aware chunks below the model limit."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = []
    count = 0

    for sentence in sentences:
        words = sentence.split()
        while len(words) > max_words:
            if current:
                chunks.append(" ".join(current))
                current, count = [], 0
            chunks.append(" ".join(words[:max_words]))
            words = words[max_words:]
        if words and count + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current, count = [], 0
        if words:
            current.append(" ".join(words))
            count += len(words)

    if current:
        chunks.append(" ".join(current))
    return chunks


def translate_to_meiteilon(text: str, target_lang: str) -> str:
    target_aliases = {
        "mni-mtei": "mni_Mtei",
        "mni_mtei": "mni_Mtei",
        "mni-beng": "mni_Beng",
        "mni_beng": "mni_Beng",
    }
    target = target_aliases.get(target_lang.lower())
    if not target:
        raise HTTPException(status_code=400, detail="Supported targets are mni-Mtei and mni-Beng.")

    with _DEVICE_LOCK:
        try:
            torch, tokenizer, model, processor, device = get_translator()
            translations = []
            for chunk in split_for_model(text):
                prepared = processor.preprocess_batch(
                    [chunk], src_lang="eng_Latn", tgt_lang=target
                )
                inputs = tokenizer(
                    prepared,
                    padding="longest",
                    truncation=True,
                    max_length=256,
                    return_tensors="pt",
                ).to(device)
                with torch.inference_mode():
                    output = model.generate(
                        **inputs,
                        use_cache=False,
                        num_beams=4,
                        num_return_sequences=1,
                        max_length=256,
                    )
                decoded = tokenizer.batch_decode(
                    output,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )
                translations.extend(processor.postprocess_batch(decoded, lang=target))
            return " ".join(translations)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "The local IndicTrans2 model could not start. Check the WSL setup, "
                    "installed requirements, and internet access for the initial model download. "
                    f"Details: {exc}"
                ),
            ) from exc


@app.post("/api/simplify")
def simplify_and_translate(payload: RequestPayload):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    plain_english = simplify_english(payload.text)
    translated = translate_to_meiteilon(plain_english, payload.target_lang)
    return {
        "status": "success",
        "engine": "AI4Bharat IndicTrans2 (local)",
        "original_text": payload.text,
        "simplified_english": plain_english,
        "translated_text": translated,
        "speak_text": plain_english,
    }


class SpeechPayload(BaseModel):
    text: str


@app.post("/api/speak")
def speak_manipuri(payload: SpeechPayload):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")
    if len(payload.text) > 1200:
        raise HTTPException(status_code=400, detail="Please request audio for a shorter passage (1,200 characters max).")

    try:
        import soundfile as sf

        with _TTS_LOCK:
            torch, model, prompt_tokenizer, description_tokenizer, device = get_speech_model()
            prompt_inputs = prompt_tokenizer(payload.text, return_tensors="pt").to(device)
            description = "Laishram speaks Manipuri in a clear, steady voice. The recording is high quality and close."
            description_inputs = description_tokenizer(description, return_tensors="pt").to(device)
            with torch.inference_mode():
                generated = model.generate(
                    input_ids=description_inputs.input_ids,
                    attention_mask=description_inputs.attention_mask,
                    prompt_input_ids=prompt_inputs.input_ids,
                    prompt_attention_mask=prompt_inputs.attention_mask,
                )
            audio = generated.detach().cpu().numpy().squeeze()

        buffer = BytesIO()
        sf.write(buffer, audio, model.config.sampling_rate, format="WAV")
        return Response(content=buffer.getvalue(), media_type="audio/wav")
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Manipuri speech generation failed. Install the TTS dependencies and allow the "
                "initial model download (about 4 GB). Details: " + str(exc)
            ),
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)




