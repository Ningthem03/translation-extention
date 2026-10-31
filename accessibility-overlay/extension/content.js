// Floating Button
const floatBtn = document.createElement('button');
floatBtn.innerText = '🔊 Simplify & Read (Manipuri)';
floatBtn.className = 'access-float-btn';
document.body.appendChild(floatBtn);

// Non-blocking UI Modal Container
const overlayModal = document.createElement('div');
overlayModal.style.cssText = `
  position: fixed;
  bottom: 80px;
  right: 25px;
  width: 320px;
  background: #ffffff;
  border: 2px solid #2563eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  z-index: 999999;
  display: none;
  font-family: system-ui, sans-serif;
  color: #1e293b;
`;
document.body.appendChild(overlayModal);

let activeAudioUrl = null;
let activeAudioPlayer = null;
let activeAudioContext = null;
let activeAudioSource = null;

function unlockAudioFromClick() {
  const Context = window.AudioContext || window.webkitAudioContext;
  if (!Context) return null;

  try {
    activeAudioContext = new Context();
    // Resume immediately in the user's click handler so delayed model output
    // can still play when it arrives.
    activeAudioContext.resume().catch(() => {});
    return activeAudioContext;
  } catch (_) {
    return null;
  }
}

function clearManipuriAudio() {
  if (activeAudioSource) {
    try { activeAudioSource.stop(); } catch (_) {}
    activeAudioSource = null;
  }
  if (activeAudioContext) {
    activeAudioContext.close().catch(() => {});
    activeAudioContext = null;
  }
  if (activeAudioPlayer) {
    activeAudioPlayer.pause();
    activeAudioPlayer.removeAttribute('src');
    activeAudioPlayer.load();
    activeAudioPlayer.remove();
    activeAudioPlayer = null;
  }
  if (activeAudioUrl) {
    URL.revokeObjectURL(activeAudioUrl);
    activeAudioUrl = null;
  }
}

function triggerSpeech(textToSpeak, language) {
  if (!textToSpeak) return null;

  const utterance = new SpeechSynthesisUtterance(textToSpeak);
  utterance.lang = language;
  utterance.rate = 0.85;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  const voices = window.speechSynthesis.getVoices();
  const languagePrefix = language.toLowerCase().split('-')[0];
  const selectedVoice = voices.find(v => v.lang.toLowerCase() === language.toLowerCase())
    || voices.find(v => v.lang.toLowerCase().startsWith(`${languagePrefix}-`));
  
  if (selectedVoice) {
    utterance.voice = selectedVoice;
  }
  
  window.speechSynthesis.speak(utterance);
  return utterance;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
}

floatBtn.addEventListener('click', async () => {
  clearManipuriAudio();
  const playbackContext = unlockAudioFromClick();
  const selectedText = window.getSelection().toString() || document.body.innerText.substring(0, 300);
  if (!selectedText) {
    overlayModal.style.display = 'block';
    overlayModal.innerHTML = '<strong>Notice:</strong> Please highlight text on the web page first!';
    return;
  }

  floatBtn.innerText = 'Processing...';

  try {
    const response = await fetch('http://localhost:8000/api/simplify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: selectedText, target_lang: 'mni-Mtei' })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Translation failed (HTTP ${response.status}).` );

    // Render output into non-blocking custom modal
    overlayModal.style.display = 'block';
    overlayModal.innerHTML = `
      <div style="display:flex; justify-size:space-between; align-items:center; margin-bottom:8px;">
        <strong style="color:#2563eb;">Regional Accessibility Overlay</strong>
        <button id="closeOverlay" style="background:none; border:none; cursor:pointer; font-weight:bold;">✕</button>
      </div>
      <div style="margin-bottom:8px;">
        <small style="color:#64748b; font-weight:600;">SIMPLIFIED ENGLISH:</small>
        <p style="margin:4px 0 8px 0; font-size:13px;">${escapeHtml(data.simplified_english)}</p>
      </div>
      <div>
        <small style="color:#64748b; font-weight:600;">MANIPURI (MEITEI MAYEK):</small>
        <p style="margin:4px 0 0 0; font-size:15px; font-weight:bold; color:#0f172a;">${escapeHtml(data.translated_text)}</p>
      </div>
      <button id="playManipuri" style="margin-top:12px;padding:8px 12px;border:0;border-radius:8px;background:#2563eb;color:#fff;cursor:pointer;">Retry Manipuri audio</button>
      <span id="audioStatus" style="display:block;margin-top:6px;font-size:12px;color:#64748b;"></span>
    `;

    overlayModal.querySelector('#closeOverlay').onclick = () => {
      overlayModal.style.display = 'none';
      window.speechSynthesis.cancel();
      clearManipuriAudio();
    };

    // English uses the browser voice; Manipuri audio is synthesized by the backend.
    window.speechSynthesis.cancel();
    triggerSpeech(data.speak_text, 'en-IN');
    const playButton = overlayModal.querySelector('#playManipuri');
    const audioStatus = overlayModal.querySelector('#audioStatus');
    const generateAndPlayManipuri = async context => {
      playButton.disabled = true;
      audioStatus.textContent = 'Generating Manipuri voice…';
      try {
        const audioResponse = await fetch('http://localhost:8000/api/speak', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: data.translated_text })
        });
        if (!audioResponse.ok) {
          const failure = await audioResponse.json().catch(() => ({}));
          throw new Error(failure.detail || `Audio generation failed (HTTP ${audioResponse.status}).`);
        }

        const audioBlob = await audioResponse.blob();
        activeAudioUrl = URL.createObjectURL(audioBlob);
        activeAudioPlayer = document.createElement('audio');
        activeAudioPlayer.controls = true;
        activeAudioPlayer.preload = 'metadata';
        activeAudioPlayer.style.cssText = 'display:block;width:100%;margin-top:8px;';
        activeAudioPlayer.src = activeAudioUrl;
        audioStatus.insertAdjacentElement('afterend', activeAudioPlayer);

        if (context && activeAudioContext === context) {
          await context.resume();
          const buffer = await context.decodeAudioData(await audioBlob.arrayBuffer());
          const source = context.createBufferSource();
          source.buffer = buffer;
          source.connect(context.destination);
          activeAudioSource = source;
          source.onended = () => { if (activeAudioSource === source) activeAudioSource = null; };
          source.start();
          audioStatus.textContent = 'Playing Manipuri audio. Use the player to replay it.';
        } else {
          audioStatus.textContent = 'Audio ready. Press play in the player.';
        }
      } catch (audioError) {
        audioStatus.textContent = audioError.message || 'Could not generate Manipuri audio.';
      } finally {
        playButton.disabled = false;
      }
    };

    playButton.onclick = () => {
      clearManipuriAudio();
      const retryContext = unlockAudioFromClick();
      void generateAndPlayManipuri(retryContext);
    };
    void generateAndPlayManipuri(playbackContext);

  } catch (err) {
    overlayModal.style.display = 'block';
    overlayModal.textContent = err.message || 'Backend error. Ensure the backend is running on http://localhost:8000.';
  } finally {
    floatBtn.innerText = '🔊 Simplify & Read (Manipuri)';
  }
});


