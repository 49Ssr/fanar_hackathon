(function () {
  var currentLocation = null;
  var voiceReady = false;
  var recognition = null;
  var auraVoiceMode = false;
  var lastAudioUrl = null;

  function apiBase() {
    return window.QAARIB_API_BASE || 'http://localhost:5000';
  }

  function status(msg) {
    console.log('[Qaarib voice/location]', msg);
    var input = document.getElementById('chatInput');
    if (input && msg) input.setAttribute('data-status', msg);
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

  function requestMic() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      status('microphone not supported');
      return Promise.resolve(false);
    }
    return navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      stream.getTracks().forEach(function (track) { track.stop(); });
      voiceReady = true;
      status('microphone ready');
      return true;
    }).catch(function () {
      status('microphone denied or unavailable');
      return false;
    });
  }

  function setupSpeechRecognition() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;
    var rec = new SpeechRecognition();
    rec.lang = 'en-QA';
    rec.interimResults = false;
    rec.continuous = false;
    rec.maxAlternatives = 1;
    rec.onresult = function (event) {
      var text = event.results && event.results[0] && event.results[0][0] ? event.results[0][0].transcript : '';
      var input = document.getElementById('chatInput');
      if (input && text) {
        input.value = text;
        input.focus();
        auraVoiceMode = true;
        if (typeof window.sendMessage === 'function') window.sendMessage();
      }
    };
    rec.onerror = function (event) { status('voice error: ' + (event.error || 'unknown')); };
    rec.onend = function () {
      var btn = document.querySelector('.input-action[title="Voice"]');
      if (btn) btn.textContent = '🎙';
    };
    return rec;
  }

  function startVoice() {
    var input = document.getElementById('chatInput');
    var btn = document.querySelector('.input-action[title="Voice"]');
    auraVoiceMode = true;
    if (btn) btn.textContent = '●';
    Promise.all([requestLocation(), requestMic()]).then(function () {
      recognition = recognition || setupSpeechRecognition();
      if (!recognition) {
        if (input) input.placeholder = 'Voice not supported here — type your request…';
        if (btn) btn.textContent = '🎙';
        return;
      }
      try {
        recognition.start();
        status('listening');
      } catch (e) {
        status('voice already listening');
      }
    });
  }

  function playAura(text) {
    if (!auraVoiceMode || !text) return;
    var clean = String(text).replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim();
    if (!clean) return;
    status('Fanar Aura speaking');
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
  window.QAARIB_PLAY_AURA = playAura;
  window.QAARIB_AURA_MODE = function (enabled) { auraVoiceMode = enabled !== false; };

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('.input-action[title="Voice"]');
    if (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        startVoice();
      });
    }
    var intro = document.getElementById('intro-ui');
    if (intro) intro.addEventListener('click', function () { requestLocation(); });
    setTimeout(function () { requestLocation(); }, 900);
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      if (wrapAppendBotText() || tries > 20) clearInterval(timer);
    }, 250);
  });
})();
