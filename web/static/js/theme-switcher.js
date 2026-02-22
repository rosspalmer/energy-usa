(function () {
  var stored = typeof localStorage !== 'undefined' && localStorage.getItem('energy-usa-theme');
  var theme = stored || 'day';
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    var dayBtn = document.getElementById('theme-day');
    var nightBtn = document.getElementById('theme-night');
    if (dayBtn) dayBtn.setAttribute('aria-pressed', t === 'day' ? 'true' : 'false');
    if (nightBtn) nightBtn.setAttribute('aria-pressed', t === 'night' ? 'true' : 'false');
    if (typeof localStorage !== 'undefined') localStorage.setItem('energy-usa-theme', t);
  }
  applyTheme(theme);
  document.getElementById('theme-day') && document.getElementById('theme-day').addEventListener('click', function () { applyTheme('day'); });
  document.getElementById('theme-night') && document.getElementById('theme-night').addEventListener('click', function () { applyTheme('night'); });
})();
