# Run the translation backend in WSL2 (Ubuntu)

The backend uses a public IndicTrans2 mirror for English-to-Manipuri translation and Indic Parler-TTS for Manipuri speech. The translation model supports Meitei Mayek (`mni_Mtei`) and Bengali script (`mni_Beng`). The speech model includes Manipuri voices, so audio does not depend on a Manipuri voice being installed in Windows. Both models load on first use and remain cached in memory. CPU speech generation can take a while.

The TTS model requires Python 3.12 and Transformers 4.46.1. The previous Python 3.14 translation environment can remain untouched. Create a compatible environment in WSL and install the backend requirements:

```powershell
wsl -d Ubuntu -- bash -lc "~/.venvs/translation-overlay/bin/uv venv --python 3.12 ~/.venvs/translation-overlay-tts && cd '/mnt/c/DULO Hack/translation-extention/accessibility-overlay/backend' && ~/.venvs/translation-overlay/bin/uv pip install --python ~/.venvs/translation-overlay-tts/bin/python -r requirements.txt"
```

Then start the backend from PowerShell with:

```powershell
wsl -d Ubuntu -- bash -lc "cd '/mnt/c/DULO Hack/translation-extention/accessibility-overlay/backend' && HF_HUB_DISABLE_XET=1 ~/.venvs/translation-overlay-tts/bin/python main.py"
```

The API remains available to the browser extension at `http://localhost:8000`. The translation checkpoint is about 1.1 GB. The speech checkpoint is about 4 GB. Both download from their public Hugging Face mirrors on first use; later starts use the local cache. After changing `extension/content.js`, reload the unpacked extension at `chrome://extensions`.





