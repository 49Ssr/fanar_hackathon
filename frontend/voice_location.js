(function () {
  var currentLocation = null;
  var voiceReady = false;
  var recognition = null;
  var isListening = false;
  var finalTranscript = '';
  var interimTranscript = '';
  var auraVoiceMode = false;
  var lastAudioUrl = null;
  var selectedMicId = 'default';
  var selectedSpeakerId = 'default';
  var auraPlaybackRate = 0.78;
  var manualStop = false;

  function apiBase() {
    return window.QAARIB_API_BASE || 'http://localhost:5000';
  }

  function el(id) { return document.getElementById(id); }

  function status(msg) {
    console.log('[Qaarib voice/location]', msg);
    var input = el('chatInput');
    var pill = el('qaaribVoiceStatus');
    if (input && msg) input.setAttribute('data-status', msg);
    if (pill) pill.textContent = msg;
  }

  function ensureVoicePanel() {
    if (el('qaaribVoicePanel')) return;

    var panel = document.createElement('div');
    panel.id = 'qaaribVoicePanel';
    panel.style.cssText = 'position:fixed;right:18px;bottom:92px;z-index:450;background:rgba(18,18,18,.96);border:1px solid #333;border-radius:14px;padding:12px;width:310px;color:#f0ece3;font-family:system-ui,-apple-system,Segoe UI,sans-serif;box-shadow:0 10px 38px rgba(0,0,0,.5);display:none;';
    panel.innerHTML = '' +
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">' +
        '<div style="font-weight:700;font-size:14px;">Voice controls</div>' +
        '<button id="qaaribCloseVoicePanel" style="background:transparent;border:0;color:#aaa;font-size:18px;cursor:pointer;">×</button>' +
      '</div>' +
      '<div id="qaaribVoiceStatus" style="font-size:12px;color:#c9a84c;margin-bottom:10px;">idle</div>' +
      '<label style="font-size:12px;color:#aaa;display:block;margin-bottom:4px;">Microphone</label>' +
      '<select id="qaaribMicSelect" style="width:100%;background:#0e0e0e;color:#fff;border:1px solid #333;border-radius:8px;padding:8px;margin-bottom:10px;"><option value="default">Device default</option></select>' +
      '<label style="font-size:12px;color:#aaa;display:block;margin-bottom:4px;">Speaker</label>' +
      '<select id="qaaribSpeakerSelect" style="width:100%;background:#0e0e0e;color:#fff;border:1px solid #333;border-radius:8px;padding:8px;margin-bottom:10px;"><option value="default">Device default</option></select>' +
      '<label style="font-size:12px;color:#aaa;display:block;margin-bottom:4px;">Aura speed</label>' +
      '<select id="qaaribSpeedSelect" style="width:100%;background:#0e0e0e;color:#fff;border:1px solid #333;border-radius:8px;padding:8px;margin-bottom:10px;">' +
        '<option value="0.70">Slow</option><option value="0.78" selected>Natural slow</option><option value="0.88">Normal-ish</option><option value="1">Raw</option>' +
      '</select>' +
      '<button id="qaaribRefreshDevices" style="width:100%;background:#c9a84c;color:#111;border:0;border-radius:8px;padding:9px;font-weight:700;cursor:pointer;">Refresh devices</button>' +
      '<div style="font-size:11px;color:#777;line-height:1.4;margin-top:9px;">Note: Chrome/Edge allow speaker selection. Browser speech recognition may still use the system/default mic even after selection.</div>';
    document.body.appendChild(panel);

    el('qaaribCloseVoicePanel').onclick = function () { panel.style.display = 'none'; };
    el('qaaribRefreshDevices').onclick = function () { enumerateDevices(true); };
    el('qaaribMicSelect').onchange = function (e) { selectedMicId = e.target.value || 'default'; requestMic(); };
    el('qaaribSpeakerSelect').onchange = function (e) { selectedSpeakerId = e.target.value || 'default'; };
    el('qaaribSpeedSelect').onchange = function (e) { auraPlaybackRate = parseFloat(e.target.value || '0.78'); };
  }

  function showVoicePanel() {
    ensureVoicePanel();
    var panel = el('qaaribVoicePanel');
    if (panel) panel.style.display = 'block';
  }

  function setButtonListening(active) {
    var btn = document.querySelector('.input-action[title="Voice"]');
    if (!btn) return;
    btn.textContent = active ? '■' : '🎙';
    btn.style.background = active ? '#7a1f1f' : '';
    btn.style.color = active ? '#fff' : '';
    btn.title = active ? 'Stop recording' : 'Voice';
  }

  function requestLocation() {
    if (!navigator.geolocation) {
      status('location not supported');
      return Promise.resolve(null);
    }
    return new Promise(function (resolve) {
      navigator.geolocation.getCurrentPosition(function (pos) {
        currentLocation = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: Math.round(pos.coords.accuracy || 0),
          ts: Date.now()
        };
        status('location ready');
        resolve(currentLocation);
      }, function () {
        status('location denied or unavailable');
        resolve(null);
      }, { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 });
    });
  }

  function micConstraints() {
    if (selectedMicId && selectedMicId !== 'default') {
      return { audio: { deviceId: { exact: selectedMicId }, echoCancellation: true, noiseSuppression: true } };
    }
    return { audio: { echoCancellation: true, noiseSuppression: true } };
  }

  function requestMic() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      status('microphone not supported');
      return Promise.resolve(false);
    }
    return navigator.mediaDevices.getUserMedia(micConstraints()).then(function (stream) {
      stream.getTracks().forEach(function (track) { track.stop(); });
      voiceReady = true;
      status('microphone ready');
      enumerateDevices(false);
      return true;
    }).catch(function () {
      status('microphone denied or unavailable');
      return false;
    });
  }

  function enumerateDevices(forcePermission) {
    ensureVoicePanel();
    var p = forcePermission ? requestMic() : Promise.resolve(true);
    return p.then(function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      return navigator.mediaDevices.enumerateDevices().then(function (devices) {
        var mic = el('qaaribMicSelect');
        var spk = el('qaaribSpeakerSelect');
        if (!mic || !spk) return;
        var oldMic = selectedMicId;
        var oldSpk = selectedSpeakerId;
        mic.innerHTML = '<option value="default">Device default</option>';
        spk.innerHTML = '<option value="default">Device default</option>';
        var micCount = 1, spkCount = 1;
        devices.forEach(function (d) {
          if (d.kind === 'audioinput') {
            var opt = document.createElement('option');
            opt.value = d.deviceId;
            opt.textContent = d.label || ('Microphone ' + micCount++);
            mic.appendChild(opt);
          }
          if (d.kind === 'audiooutput') {
            var opt2 = document.createElement('option');
            opt2.value = d.deviceId;
            opt2.textContent = d.label || ('Speaker ' + spkCount++);
            spk.appendChild(opt2);
          }
        });
        mic.value = oldMic;
        spk.value = oldSpk;
        status('devices ready');
      });
    });
  }

  function setupSpeechRecognition() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;
    var rec = new SpeechRecognition();
    rec.lang = 'en-QA';
    rec.interimResults = true;
    rec.continuous = true;
    rec.maxAlternatives = 1;
    rec.onstart = function () {
      isListening = true;
      manualStop = false;
      finalTranscript = '';
      interimTranscript = '';
      setButtonListening(true);
      status('listening... click ■ to stop');
    };
    rec.onresult = function (event) {
      interimTranscript = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalTranscript += t + ' ';
        else interimTranscript += t;
      }
      var input = el('chatInput');
      if (input) {
        input.value = (finalTranscript + interimTranscript).trim();
        input.placeholder = interimTranscript ? 'Listening…' : 'Heard you — click stop when done';
      }
      status('hearing: ' + ((finalTranscript + interimTranscript).trim() || '...'));
    };
    rec.onerror = function (event) {
      status('voice error: ' + (event.error || 'unknown'));
    };
    rec.onend = function () {
      isListening = false;
      setButtonListening(false);
      var input = el('chatInput');
      var text = ((finalTranscript + interimTranscript).trim() || (input ? input.value.trim() : ''));
      if (manualStop && input && text) {
        input.value = text;
        auraVoiceMode = true;
        status('voice captured — sending');
        if (typeof window.sendMessage === 'function') window.sendMessage();
      } else {
        status(text ? 'voice captured' : 'no speech captured');
      }
      if (input) input.placeholder = 'Ask Qaarib anything…';
    };
    return rec;
  }

  function startVoice() {
    showVoicePanel();
    auraVoiceMode = true;
    Promise.all([requestLocation(), requestMic()]).then(function () {
      recognition = recognition || setupSpeechRecognition();
      if (!recognition) {
        var input = el('chatInput');
        if (input) input.placeholder = 'Voice not supported here — type your request…';
        setButtonListening(false);
        status('voice recognition not supported');
        return;
      }
      try { recognition.start(); }
      catch (e) { status('voice already listening'); }
    });
  }

  function stopVoice() {
    manualStop = true;
    status('stopping...');
    try {
      if (recognition) recognition.stop();
    } catch (e) {
      setButtonListening(false);
      status('stopped');
    }
  }

  function toggleVoice() {
    if (isListening) stopVoice();
    else startVoice();
  }

  function playAura(text) {
    if (!auraVoiceMode || !text) return;
    var clean = String(text).replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim();
    if (!clean) return;
    status('Fanar Aura preparing');
    fetch(apiBase() + '/aura_tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: clean })
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Aura unavailable');
        return res.blob();
      })
      .then(function (blob) {
        if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);
        lastAudioUrl = URL.createObjectURL(blob);
        var audio = new Audio(lastAudioUrl);
        audio.playbackRate = auraPlaybackRate;
        if (selectedSpeakerId && selectedSpeakerId !== 'default' && audio.setSinkId) {
          audio.setSinkId(selectedSpeakerId).catch(function () {});
        }
        status('Fanar Aura speaking');
        audio.play().catch(function () { status('tap page to allow audio playback'); });
      })
      .catch(function () {
        status('Fanar Aura unavailable; text reply only');
      });
  }

  function wrapAppendBotText() {
    if (typeof window.appendBotText !== 'function' || window.appendBotText.__auraWrapped) return false;
    var original = window.appendBotText;
    window.appendBotText = function (text) {
      original(text);
      playAura(text);
    };
    window.appendBotText.__auraWrapped = true;
    return true;
  }

  var originalFetch = window.fetch.bind(window);
  window.fetch = function (url, options) {
    try {
      var urlText = String(url || '');
      if (urlText.indexOf('/chat') !== -1 && options && options.body) {
        var body = JSON.parse(options.body);
        if (currentLocation && !body.location) body.location = currentLocation;
        options.body = JSON.stringify(body);
      }
    } catch (e) {}
    return originalFetch(url, options);
  };

  window.QAARIB_LOCATION = function () { return currentLocation; };
  window.QAARIB_REQUEST_LOCATION = requestLocation;
  window.QAARIB_START_VOICE = startVoice;
  window.QAARIB_STOP_VOICE = stopVoice;
  window.QAARIB_TOGGLE_VOICE = toggleVoice;
  window.QAARIB_PLAY_AURA = playAura;
  window.QAARIB_AURA_MODE = function (enabled) { auraVoiceMode = enabled !== false; };

  document.addEventListener('DOMContentLoaded', function () {
    ensureVoicePanel();
    var btn = document.querySelector('.input-action[title="Voice"]');
    if (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        toggleVoice();
      });
      btn.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        showVoicePanel();
      });
    }
    var intro = el('intro-ui');
    if (intro) intro.addEventListener('click', function () { requestLocation(); });
    setTimeout(function () { requestLocation(); enumerateDevices(false); }, 900);
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      if (wrapAppendBotText() || tries > 20) clearInterval(timer);
    }, 250);
  });
})();
