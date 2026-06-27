(function () {
  var stream = null;
  var audioCtx = null;
  var analyser = null;
  var raf = null;

  function el(id) { return document.getElementById(id); }

  function ensureWaveUI() {
    if (!el('qaaribWaveStyle')) {
      var style = document.createElement('style');
      style.id = 'qaaribWaveStyle';
      style.textContent = '' +
        '#qaaribWaveFloat{position:fixed;left:50%;bottom:142px;transform:translateX(-50%);z-index:470;display:none;background:rgba(13,13,13,.96);border:1px solid #2a2a2a;border-radius:999px;padding:8px 12px;box-shadow:0 10px 32px rgba(0,0,0,.45)}' +
        '#qaaribWaveCanvas{width:180px;height:38px;display:block;background:#0b0b0b;border:1px solid #242424;border-radius:999px}';
      document.head.appendChild(style);
    }
    if (!el('qaaribWaveFloat')) {
      var wrap = document.createElement('div');
      wrap.id = 'qaaribWaveFloat';
      wrap.innerHTML = '<canvas id="qaaribWaveCanvas" width="360" height="76"></canvas>';
      document.body.appendChild(wrap);
    }
  }

  function drawIdle() {
    ensureWaveUI();
    var c = el('qaaribWaveCanvas');
    var ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.strokeStyle = 'rgba(201,168,76,.25)';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(20, c.height / 2);
    ctx.lineTo(c.width - 20, c.height / 2);
    ctx.stroke();
  }

  function drawLive() {
    var c = el('qaaribWaveCanvas');
    if (!c || !analyser) return;
    var ctx = c.getContext('2d');
    var data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#c9a84c';
    ctx.beginPath();
    for (var i = 0; i < data.length; i++) {
      var x = i * c.width / (data.length - 1);
      var y = (data[i] / 255) * c.height;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    raf = requestAnimationFrame(drawLive);
  }

  function startWaveform() {
    ensureWaveUI();
    var box = el('qaaribWaveFloat');
    if (box) box.style.display = 'block';
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      drawIdle();
      return;
    }
    stopWaveform(false);
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
      stream = s;
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume().catch(function () {});
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      drawLive();
    }).catch(function () {
      drawIdle();
    });
  }

  function stopWaveform(hide) {
    if (raf) cancelAnimationFrame(raf);
    raf = null;
    analyser = null;
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    stream = null;
    drawIdle();
    if (hide !== false) {
      var box = el('qaaribWaveFloat');
      if (box) setTimeout(function () { box.style.display = 'none'; }, 700);
    }
  }

  function attach() {
    ensureWaveUI();
    drawIdle();
    var btn = document.querySelector('.input-action[title="Voice"], .input-action[title="Stop recording"]');
    if (!btn || btn.__qaaribWaveAttached) return;
    btn.__qaaribWaveAttached = true;
    btn.addEventListener('click', function () {
      setTimeout(function () {
        var active = btn.textContent === '■' || btn.classList.contains('qaarib-recording');
        if (active) startWaveform();
        else stopWaveform(true);
      }, 180);
    });
  }

  window.QAARIB_START_WAVEFORM = startWaveform;
  window.QAARIB_STOP_WAVEFORM = stopWaveform;

  document.addEventListener('DOMContentLoaded', function () {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      attach();
      if (tries > 40) clearInterval(timer);
    }, 250);
  });
})();
