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

function triggerSpeech(textToSpeak) {
  if (!textToSpeak) return;
  
  window.speechSynthesis.cancel();
  
  const utterance = new SpeechSynthesisUtterance(textToSpeak);
  utterance.rate = 0.85;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  const voices = window.speechSynthesis.getVoices();
  const selectedVoice = voices.find(v => v.lang.includes('hi') || v.lang.includes('en-IN') || v.lang.includes('en')) || voices[0];
  
  if (selectedVoice) {
    utterance.voice = selectedVoice;
  }
  
  window.speechSynthesis.speak(utterance);
}

floatBtn.addEventListener('click', async () => {
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

    // Render output into non-blocking custom modal
    overlayModal.style.display = 'block';
    overlayModal.innerHTML = `
      <div style="display:flex; justify-size:space-between; align-items:center; margin-bottom:8px;">
        <strong style="color:#2563eb;">Regional Accessibility Overlay</strong>
        <button id="closeOverlay" style="background:none; border:none; cursor:pointer; font-weight:bold;">✕</button>
      </div>
      <div style="margin-bottom:8px;">
        <small style="color:#64748b; font-weight:600;">SIMPLIFIED ENGLISH:</small>
        <p style="margin:4px 0 8px 0; font-size:13px;">${data.simplified_english}</p>
      </div>
      <div>
        <small style="color:#64748b; font-weight:600;">MANIPURI (MEITEI MAYEK):</small>
        <p style="margin:4px 0 0 0; font-size:15px; font-weight:bold; color:#0f172a;">${data.translated_text}</p>
      </div>
    `;

    document.getElementById('closeOverlay').onclick = () => {
      overlayModal.style.display = 'none';
      window.speechSynthesis.cancel();
    };

    // Play speech output
    triggerSpeech(data.speak_text);

  } catch (err) {
    overlayModal.style.display = 'block';
    overlayModal.innerHTML = '<strong>Backend Error:</strong> Ensure backend is running on http://localhost:8000';
  } finally {
    floatBtn.innerText = '🔊 Simplify & Read (Manipuri)';
  }
});
