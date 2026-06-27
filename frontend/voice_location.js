(function () {
  var currentLocation = null;
  var recognition = null;
  var isListening = false;
  var manualStop = false;
  var finalTranscript = '';
  var interimTranscript = '';
  var selectedMicId = 'default';
  var selectedSpeakerId = 'default';
  var auraVoiceMode = false;
  var auraPlaybackRate = 0.68;
  var lastAudioUrl = null;
  var recordStartedAt = 0;
  var statusTimer = null;

  function apiBase() { return window.QAARIB_API_BASE || 'http://localhost:5000'; }
  function el(id) { return document.getElementById(id); }

  function status(msg) {
    console.log('[Qaarib voice]', msg);
    var pill = el('qaaribVoiceStatus');
    if (pill) pill.textContent = msg || '';
  }

  function ensureStyles() {
    if (el('qaaribVoiceStyles')) return;
    var s = document.createElement('style');
    s.id = 'qaaribVoiceStyles';
    s.textContent = '' +
      '#qaaribVoicePill{position:fixed;left:50%;bottom:92px;transform:translateX(-50%);z-index:460;background:rgba(13,13,13,.96);border:1px solid #2a2a2a;border-radius:999px;padding:9px 14px;color:#f0ece3;font:12px system-ui,-apple-system,Segoe UI,sans-serif;display:none;align-items:center;gap:10px;box-shadow:0 10px 32px rgba(0,0,0,.45)}' +
      '#qaaribVoiceDot{width:8px;height:8px;border-radius:50%;background:#777}' +
      '#qaaribVoicePill.listening #qaaribVoiceDot{background:#c9a84c;animation:qaaribPulse 900ms ease-in-out infinite;box-shadow:0 0 16px rgba(201,168,76,.9)}' +
      '@keyframes qaaribPulse{0%,100%{transform:scale(1);opacity:.7}50%{transform:scale(1.55);opacity:1}}' +
      '#qaaribVoiceTimer{color:#888;font-variant-numeric:tabular-nums}' +
      '#qaaribVoicePanel{position:fixed;right:18px;bottom:92px;z-index:450;background:rgba(13,13,13,.97);border:1px solid #2a2a2a;border-radius:12px;padding:12px;width:min(320px,calc(100vw - 32px));color:#f0ece3;font:13px system-ui,-apple-system,Segoe UI,sans-serif;box-shadow:0 12px 38px rgba(0,0,0,.55);display:none}' +
      '#qaaribVoicePanel select,#qaaribVoicePanel button{width:100%;background:#111;color:#f0ece3;border:1px solid #2a2a2a;border-radius:8px;padding:8px;margin:4px 0 10px;font:13px system-ui,-apple-system,Segoe UI,sans-serif}' +
      '#qaaribVoicePanel button{background:#1a1a1a;cursor:pointer}' +
      '#qaaribVoicePanel label{font-size:11px;color:#888;display:block;margin-top:4px}' +
      '#qaaribVoicePanel .close{width:auto;border:0;background:transparent;color:#888;margin:0;padding:0 4px;font-size:18px}' +
      '.input-action.qaarib-recording{background:#2a2112!important;color:#fff!important;border-color:#66562a!important}';
    document.head.appendChild(s);
  }

  function ensureUI() {
    ensureStyles();
    if (!el('qaaribVoicePill')) {
      var pill = document.createElement('div');
      pill.id = 'qaaribVoicePill';
      pill.innerHTML = '<span id="qaaribVoiceDot"></span><span id="qaaribVoiceStatus">ready</span><span id="qaaribVoiceTimer">00:00</span>';
      document.body.appendChild(pill);
    }
    if (!el('qaaribVoicePanel')) {
      var panel = document.createElement('div');
      panel.id = 'qaaribVoicePanel';
      panel.innerHTML = '' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><b style="font-size:13px">Voice settings</b><button class="close" id="qaaribCloseVoicePanel">×</button></div>' +
        '<label>Microphone permission / browser input</label><select id="qaaribMicSelect"><option value="default">Device default</option></select>' +
        '<label>Speaker</label><select id="qaaribSpeakerSelect"><option value="default">Device default</option></select>' +
        '<label>Aura speed</label><select id="qaaribSpeedSelect"><option value="0.60">Very slow</option><option value="0.68" selected>Slow</option><option value="0.76">Natural</option><option value="0.88">Faster</option></select>' +
        '<button id="qaaribRefreshDevices">Refresh devices</button>' +
        '<div style="font-size:11px;color:#777;line-height:1.4">Click 🎙 once, speak, then click ■ to stop and send. Browser speech recognition uses its own mic path, so set your mic as OS default for the safest demo.</div>';
      document.body.appendChild(panel);
      el('qaaribCloseVoicePanel').onclick = function () { panel.style.display = 'none'; };
      el('qaaribRefreshDevices').onclick = function () { enumerateDevices(true); };
      el('qaaribMicSelect').onchange = function (e) { selectedMicId = e.target.value || 'default'; primeMicPermission(); };
      el('qaaribSpeakerSelect').onchange = function (e) { selectedSpeakerId = e.target.value || 'default'; };
      el('qaaribSpeedSelect').onchange = function (e) { auraPlaybackRate = parseFloat(e.target.value || '0.68'); };
    }
  }

  function showPill(show) {
    ensureUI();
    var pill = el('qaaribVoicePill');
    if (pill) pill.style.display = show ? 'flex' : 'none';
  }

  function setListeningUI(active) {
    var btn = document.querySelector('.input-action[title="Voice"], .input-action[title="Stop recording"]');
    showPill(true);
    if (btn) {
      btn.textContent = active ? '■' : '🎙';
      btn.title = active ? 'Stop recording' : 'Voice';
      btn.classList.toggle('qaarib-recording', active);
    }
    var pill = el('qaaribVoicePill');
    if (pill) pill.classList.toggle('listening', active);
  }

  function startTimer() {
    recordStartedAt = Date.now();
    if (statusTimer) clearInterval(statusTimer);
    statusTimer = setInterval(function () {
      var t = Math.floor((Date.now() - recordStartedAt) / 1000);
      var timer = el('qaaribVoiceTimer');
      if (timer) timer.textContent = String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0');
    }, 250);
  }

  function stopTimer() {
    if (statusTimer) clearInterval(statusTimer);
    statusTimer = null;
  }

  function micConstraints() {
    if (selectedMicId && selectedMicId !== 'default') {
      return { audio: { deviceId: { exact: selectedMicId }, echoCancellation: true, noiseSuppression: true, autoGainControl: true } };
    }
    return { audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } };
  }

  function primeMicPermission() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return Promise.resolve(false);
    return navigator.mediaDevices.getUserMedia(micConstraints()).then(function (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      status('mic permission ready');
      enumerateDevices(false);
      return true;
    }).catch(function () {
      status('mic permission blocked');
      return false;
    });
  }

  function enumerateDevices(forcePermission) {
    ensureUI();
    var p = forcePermission ? primeMicPermission() : Promise.resolve(true);
    return p.then(function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      return navigator.mediaDevices.enumerateDevices().then(function (devices) {
        var mic = el('qaaribMicSelect');
        var spk = el('qaaribSpeakerSelect');
        if (!mic || !spk) return;
        var oldMic = selectedMicId, oldSpk = selectedSpeakerId;
        mic.innerHTML = '<option value="default">Device default</option>';
        spk.innerHTML = '<option value="default">Device default</option>';
        var mi = 1, si = 1;
        devices.forEach(function (d) {
          if (d.kind === 'audioinput') {
            var o = document.createElement('option');
            o.value = d.deviceId;
            o.textContent = d.label || ('Microphone ' + mi++);
            mic.appendChild(o);
          } else if (d.kind === 'audiooutput') {
            var p = document.createElement('option');
            p.value = d.deviceId;
            p.textContent = d.label || ('Speaker ' + si++);
            spk.appendChild(p);
          }
        });
        mic.value = oldMic;
        spk.value = oldSpk;
      });
    });
  }

  function requestLocation() {
    if (!navigator.geolocation) return Promise.resolve(null);
    return new Promise(function (resolve) {
      navigator.geolocation.getCurrentPosition(function (pos) {
        currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: Math.round(pos.coords.accuracy || 0), ts: Date.now() };
        resolve(currentLocation);
      }, function () { resolve(null); }, { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 });
    });
  }

  function setupRecognition() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;
    var rec = new SpeechRecognition();
    rec.lang = 'en-US';
    rec.interimResults = true;
    rec.continuous = true;
    rec.maxAlternatives = 1;
    rec.onstart = function () {
      isListening = true;
      setListeningUI(true);
      startTimer();
      status('listening — speak now');
    };
    rec.onaudiostart = function () { status('mic opened by browser'); };
    rec.onspeechstart = function () { status('speech detected'); };
    rec.onresult = function (event) {
      interimTranscript = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalTranscript += t + ' ';
        else interimTranscript += t;
      }
      var heard = (finalTranscript + interimTranscript).trim();
      var input = el('chatInput');
      if (input) input.value = heard;
      status(heard ? ('heard: ' + heard.slice(-55)) : 'listening — speak now');
    };
    rec.onerror = function (event) {
      status('speech engine: ' + (event.error || 'error'));
    };
    rec.onend = function () {
      isListening = false;
      setListeningUI(false);
      stopTimer();
      var input = el('chatInput');
      var text = ((finalTranscript + interimTranscript).trim() || (input ? input.value.trim() : ''));
      if (manualStop && input && text) {
        input.value = text;
        auraVoiceMode = true;
        status('voice captured — sending');
        if (typeof window.sendMessage === 'function') window.sendMessage();
      } else if (manualStop) {
        status('nothing transcribed — type or try Chrome/Edge');
      } else {
        status('speech engine stopped — click mic again');
      }
      if (input) input.placeholder = 'Ask Qaarib anything…';
    };
    return rec;
  }

  function startVoice() {
    ensureUI();
    showPill(true);
    auraVoiceMode = true;
    manualStop = false;
    finalTranscript = '';
    interimTranscript = '';
    var input = el('chatInput');
    if (input) { input.value = ''; input.placeholder = 'Listening… click ■ to stop'; }
    requestLocation();
    status('starting mic...');
    primeMicPermission().then(function () {
      recognition = setupRecognition();
      if (!recognition) {
        status('speech recognition unsupported — use Chrome/Edge');
        setListeningUI(false);
        return;
      }
      try { recognition.start(); }
      catch (e) { status('speech engine busy — click again'); }
    });
  }

  function stopVoice() {
    manualStop = true;
    status('stopping...');
    try { if (recognition) recognition.stop(); }
    catch (e) {
      isListening = false;
      setListeningUI(false);
      stopTimer();
      status('stopped');
    }
  }

  function toggleVoice() { isListening ? stopVoice() : startVoice(); }

  function playAura(text) {
    if (!auraVoiceMode || !text) return;
    var clean = String(text).replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim();
    if (!clean) return;
    status('Aura preparing');
    fetch(apiBase() + '/aura_tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: clean }) })
      .then(function (res) { if (!res.ok) throw new Error('Aura unavailable'); return res.blob(); })
      .then(function (blob) {
        if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);
        lastAudioUrl = URL.createObjectURL(blob);
        var audio = new Audio(lastAudioUrl);
        audio.playbackRate = auraPlaybackRate;
        if (selectedSpeakerId && selectedSpeakerId !== 'default' && audio.setSinkId) audio.setSinkId(selectedSpeakerId).catch(function () {});
        status('Aura speaking');
        audio.play().catch(function () { status('tap page to allow audio'); });
      })
      .catch(function () { status('Aura unavailable; text reply only'); });
  }

  function wrapAppendBotText() {
    if (typeof window.appendBotText !== 'function' || window.appendBotText.__auraWrapped) return false;
    var original = window.appendBotText;
    window.appendBotText = function (text) { original(text); playAura(text); };
    window.appendBotText.__auraWrapped = true;
    return true;
  }

  var originalFetch = window.fetch.bind(window);
  window.fetch = function (url, options) {
    try {
      if (String(url || '').indexOf('/chat') !== -1 && options && options.body) {
        var body = JSON.parse(options.body);
        if (currentLocation && !body.location) body.location = currentLocation;
        options.body = JSON.stringify(body);
      }
    } catch (e) {}
    return originalFetch(url, options);
  };

  window.QAARIB_LOCATION = function () { return currentLocation; };
  window.QAARIB_REQUEST_LOCATION = requestLocation;
  window.QAARIB_TOGGLE_VOICE = toggleVoice;
  window.QAARIB_START_VOICE = startVoice;
  window.QAARIB_STOP_VOICE = stopVoice;
  window.QAARIB_PLAY_AURA = playAura;

  document.addEventListener('DOMContentLoaded', function () {
    ensureUI();
    var btn = document.querySelector('.input-action[title="Voice"]');
    if (btn) {
      btn.addEventListener('click', function (e) { e.preventDefault(); toggleVoice(); });
      btn.addEventListener('contextmenu', function (e) { e.preventDefault(); var p = el('qaaribVoicePanel'); if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none'; enumerateDevices(false); });
      btn.addEventListener('dblclick', function (e) { e.preventDefault(); var p = el('qaaribVoicePanel'); if (p) p.style.display = 'block'; enumerateDevices(true); });
    }
    var intro = el('intro-ui');
    if (intro) intro.addEventListener('click', function () { requestLocation(); });
    setTimeout(function () { requestLocation(); enumerateDevices(false); }, 900);
    var tries = 0;
    var timer = setInterval(function () { tries += 1; if (wrapAppendBotText() || tries > 20) clearInterval(timer); }, 250);
  });
})();
