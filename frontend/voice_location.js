(function () {
  var currentLocation = null;
  var recognition = null;
  var recording = false;
  var finalText = '';
  var interimText = '';
  var selectedSpeakerId = 'default';
  var auraMode = false;
  var auraSpeed = 0.68;
  var lastAudioUrl = null;
  var stream = null;
  var audioCtx = null;
  var analyser = null;
  var raf = null;
  var startedAt = 0;
  var timer = null;

  function apiBase() { return window.QAARIB_API_BASE || 'http://localhost:5000'; }
  function el(id) { return document.getElementById(id); }

  function ensureUi() {
    if (!el('qaaribVoiceStyle')) {
      var style = document.createElement('style');
      style.id = 'qaaribVoiceStyle';
      style.textContent = '' +
        '#qVoice{position:fixed;left:50%;bottom:92px;transform:translateX(-50%);z-index:500;display:none;align-items:center;gap:10px;background:rgba(13,13,13,.96);border:1px solid #2a2a2a;border-radius:999px;padding:9px 13px;color:#f0ece3;font:12px system-ui,-apple-system,Segoe UI,sans-serif;box-shadow:0 10px 32px rgba(0,0,0,.45)}' +
        '#qVoiceDot{width:8px;height:8px;border-radius:50%;background:#777;flex:0 0 auto}' +
        '#qVoice.live #qVoiceDot{background:#c9a84c;box-shadow:0 0 16px rgba(201,168,76,.85);animation:qPulse .9s ease-in-out infinite}' +
        '@keyframes qPulse{0%,100%{opacity:.65;transform:scale(1)}50%{opacity:1;transform:scale(1.45)}}' +
        '#qWave{width:190px;height:38px;background:#0b0b0b;border:1px solid #242424;border-radius:999px;display:block}' +
        '#qVoiceTime{color:#888;font-variant-numeric:tabular-nums;min-width:35px;text-align:right}' +
        '#qVoicePanel{position:fixed;right:18px;bottom:92px;z-index:490;background:rgba(13,13,13,.97);border:1px solid #2a2a2a;border-radius:12px;padding:12px;width:min(320px,calc(100vw - 32px));color:#f0ece3;font:13px system-ui,-apple-system,Segoe UI,sans-serif;box-shadow:0 12px 38px rgba(0,0,0,.55);display:none}' +
        '#qVoicePanel select,#qVoicePanel button{width:100%;background:#111;color:#f0ece3;border:1px solid #2a2a2a;border-radius:8px;padding:8px;margin:4px 0 10px;font:13px system-ui,-apple-system,Segoe UI,sans-serif}' +
        '#qVoicePanel label{font-size:11px;color:#888;display:block;margin-top:4px}' +
        '.input-action.qRec{background:#2a2112!important;color:#fff!important;border-color:#66562a!important}';
      document.head.appendChild(style);
    }
    if (!el('qVoice')) {
      var box = document.createElement('div');
      box.id = 'qVoice';
      box.innerHTML = '<span id="qVoiceDot"></span><canvas id="qWave" width="380" height="76"></canvas><span id="qVoiceTime">00:00</span>';
      document.body.appendChild(box);
    }
    if (!el('qVoicePanel')) {
      var panel = document.createElement('div');
      panel.id = 'qVoicePanel';
      panel.innerHTML = '' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><b>Voice settings</b><button id="qVoiceClose" style="width:auto;border:0;background:transparent;color:#888;margin:0;padding:0 4px;font-size:18px">×</button></div>' +
        '<label>Microphone</label><select id="qMic"><option value="default">Device default</option></select>' +
        '<label>Speaker</label><select id="qSpeaker"><option value="default">Device default</option></select>' +
        '<label>Aura speed</label><select id="qSpeed"><option value="0.60">Very slow</option><option value="0.68" selected>Slow</option><option value="0.76">Natural</option><option value="0.88">Faster</option></select>' +
        '<button id="qRefresh">Refresh devices</button>' +
        '<div style="font-size:11px;color:#777;line-height:1.4">The wave shows raw mic audio. If the wave moves but no text appears, the browser speech recognizer is the failing part.</div>';
      document.body.appendChild(panel);
      el('qVoiceClose').onclick = function () { panel.style.display = 'none'; };
      el('qRefresh').onclick = function () { listDevices(true); };
      el('qSpeaker').onchange = function (e) { selectedSpeakerId = e.target.value || 'default'; };
      el('qSpeed').onchange = function (e) { auraSpeed = parseFloat(e.target.value || '0.68'); };
    }
  }

  function setButton(active) {
    var btn = document.querySelector('.input-action[title="Voice"], .input-action[title="Stop recording"]');
    if (!btn) return;
    btn.textContent = active ? '■' : '🎙';
    btn.title = active ? 'Stop recording' : 'Voice';
    btn.classList.toggle('qRec', active);
  }

  function drawFlat() {
    var c = el('qWave');
    if (!c) return;
    var ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.strokeStyle = 'rgba(201,168,76,.25)';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(18, c.height / 2);
    ctx.lineTo(c.width - 18, c.height / 2);
    ctx.stroke();
  }

  function drawWave() {
    var c = el('qWave');
    if (!c || !analyser) return;
    var ctx = c.getContext('2d');
    var data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.strokeStyle = '#c9a84c';
    ctx.lineWidth = 4;
    ctx.beginPath();
    for (var i = 0; i < data.length; i++) {
      var x = i * c.width / (data.length - 1);
      var y = (data[i] / 255) * c.height;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    raf = requestAnimationFrame(drawWave);
  }

  function stopWave() {
    if (raf) cancelAnimationFrame(raf);
    raf = null;
    analyser = null;
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    stream = null;
    drawFlat();
  }

  function startWave() {
    ensureUi();
    el('qVoice').style.display = 'flex';
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { drawFlat(); return Promise.resolve(false); }
    stopWave();
    var mic = el('qMic') ? el('qMic').value : 'default';
    var constraints = mic && mic !== 'default' ? { audio: { deviceId: { exact: mic } } } : { audio: true };
    return navigator.mediaDevices.getUserMedia(constraints).then(function (s) {
      stream = s;
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume().catch(function () {});
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      drawWave();
      listDevices(false);
      return true;
    }).catch(function () { drawFlat(); return false; });
  }

  function listDevices(forcePermission) {
    ensureUi();
    var p = forcePermission ? startWave() : Promise.resolve(true);
    return p.then(function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      return navigator.mediaDevices.enumerateDevices().then(function (devices) {
        var mic = el('qMic'), spk = el('qSpeaker');
        if (!mic || !spk) return;
        var oldMic = mic.value || 'default', oldSpk = spk.value || 'default';
        mic.innerHTML = '<option value="default">Device default</option>';
        spk.innerHTML = '<option value="default">Device default</option>';
        var mi = 1, si = 1;
        devices.forEach(function (d) {
          var o = document.createElement('option');
          o.value = d.deviceId;
          if (d.kind === 'audioinput') { o.textContent = d.label || ('Microphone ' + mi++); mic.appendChild(o); }
          if (d.kind === 'audiooutput') { o.textContent = d.label || ('Speaker ' + si++); spk.appendChild(o); }
        });
        mic.value = oldMic; spk.value = oldSpk;
      });
    });
  }

  function startClock() {
    startedAt = Date.now();
    if (timer) clearInterval(timer);
    timer = setInterval(function () {
      var t = Math.floor((Date.now() - startedAt) / 1000);
      var out = el('qVoiceTime');
      if (out) out.textContent = String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0');
    }, 250);
  }

  function stopClock() { if (timer) clearInterval(timer); timer = null; }

  function requestLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(function (pos) {
      currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: Math.round(pos.coords.accuracy || 0), ts: Date.now() };
    }, function () {}, { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 });
  }

  function makeRecognition() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;
    var rec = new SpeechRecognition();
    rec.lang = 'en-US';
    rec.interimResults = true;
    rec.continuous = true;
    rec.maxAlternatives = 1;
    rec.onresult = function (event) {
      interimText = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var txt = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += txt + ' '; else interimText += txt;
      }
      var input = el('chatInput');
      if (input) input.value = (finalText + interimText).trim();
    };
    rec.onend = function () {
      recording = false;
      setButton(false);
      stopClock();
      stopWave();
      var input = el('chatInput');
      var text = ((finalText + interimText).trim() || (input ? input.value.trim() : ''));
      if (manualStop && input && text) { input.value = text; auraMode = true; if (typeof window.sendMessage === 'function') window.sendMessage(); }
      if (input) input.placeholder = 'Ask Qaarib anything…';
      setTimeout(function () { var q = el('qVoice'); if (q) q.style.display = 'none'; }, 900);
    };
    return rec;
  }

  function startVoice() {
    ensureUi();
    requestLocation();
    manualStop = false;
    recording = true;
    finalText = ''; interimText = '';
    var input = el('chatInput');
    if (input) { input.value = ''; input.placeholder = 'Listening… click ■ to stop'; }
    el('qVoice').classList.add('live');
    setButton(true);
    startClock();
    startWave();
    recognition = makeRecognition();
    if (recognition) { try { recognition.start(); } catch (e) {} }
  }

  function stopVoice() {
    manualStop = true;
    if (recognition) { try { recognition.stop(); return; } catch (e) {} }
    recording = false;
    setButton(false);
    stopClock(); stopWave();
  }

  function toggleVoice() { recording ? stopVoice() : startVoice(); }

  function playAura(text) {
    if (!auraMode || !text) return;
    var clean = String(text).replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim();
    if (!clean) return;
    fetch(apiBase() + '/aura_tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: clean }) })
      .then(function (res) { if (!res.ok) throw new Error('Aura unavailable'); return res.blob(); })
      .then(function (blob) {
        if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);
        lastAudioUrl = URL.createObjectURL(blob);
        var audio = new Audio(lastAudioUrl);
        audio.playbackRate = auraSpeed;
        if (selectedSpeakerId && selectedSpeakerId !== 'default' && audio.setSinkId) audio.setSinkId(selectedSpeakerId).catch(function () {});
        audio.play().catch(function () {});
      }).catch(function () {});
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

  window.QAARIB_START_VOICE = startVoice;
  window.QAARIB_STOP_VOICE = stopVoice;
  window.QAARIB_TOGGLE_VOICE = toggleVoice;
  window.QAARIB_REQUEST_LOCATION = requestLocation;

  document.addEventListener('DOMContentLoaded', function () {
    ensureUi(); drawFlat(); requestLocation(); listDevices(false);
    var btn = document.querySelector('.input-action[title="Voice"]');
    if (btn) {
      btn.addEventListener('click', function (e) { e.preventDefault(); toggleVoice(); });
      btn.addEventListener('contextmenu', function (e) { e.preventDefault(); var p = el('qVoicePanel'); if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none'; listDevices(false); });
      btn.addEventListener('dblclick', function (e) { e.preventDefault(); var p = el('qVoicePanel'); if (p) p.style.display = 'block'; listDevices(true); });
    }
    var tries = 0;
    var timer2 = setInterval(function () { tries += 1; if (wrapAppendBotText() || tries > 20) clearInterval(timer2); }, 250);
  });
})();
