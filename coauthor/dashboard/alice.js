// alice.js -- Alice conversation panel for the Coauthor SPA.
//
// Docked at bottom of the page. Sends messages to /alice endpoint.
// Persists conversation via localStorage.

(function() {
  'use strict';

  var HISTORY_KEY = 'coauthor_alice_conversation';
  var panel = null;
  var body = null;
  var msgs = null;
  var input = null;
  var toggleIcon = null;
  var statusEl = null;
  var _collapsed = true;

  function init() {
    panel = document.getElementById('alice-panel');
    if (!panel) return;

    // Guard: if panel is hidden (no LLM key), skip initialization
    if (panel.style.display === 'none') return;

    body = document.getElementById('alice-panel-body');
    msgs = document.getElementById('alice-messages');
    input = document.getElementById('alice-input');
    toggleIcon = document.getElementById('alice-toggle-icon');
    statusEl = document.getElementById('alice-status');

    // Start collapsed
    body.style.display = 'none';
    toggleIcon.textContent = '\u25B2'; // up arrow

    // Load history
    loadHistory();
  }

  function toggle() {
    _collapsed = !_collapsed;
    body.style.display = _collapsed ? 'none' : 'block';
    toggleIcon.textContent = _collapsed ? '\u25B2' : '\u25BC';
    if (!_collapsed && input) {
      setTimeout(function() { input.focus(); }, 100);
      scrollToBottom();
    }
  }

  function addMessage(text, sender) {
    if (!msgs) return;
    var div = document.createElement('div');
    div.className = 'alice-msg ' + sender;
    var time = new Date().toLocaleTimeString();
    var label = sender === 'user' ? 'You' : 'Alice';
    div.innerHTML = '<span class="alice-sender">' + label + '</span> '
      + '<span class="alice-time">' + time + '</span> '
      + text;
    msgs.appendChild(div);
    while (msgs.querySelectorAll('.alice-msg').length > 50) {
      msgs.querySelector('.alice-msg').remove();
    }
    scrollToBottom();
    saveHistory();
  }

  function scrollToBottom() {
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  function sendMessage() {
    if (!input) return;
    var text = input.value.trim();
    if (!text) return;
    input.value = '';
    addMessage(text, 'user');

    // Expand panel if collapsed
    if (_collapsed) toggle();

    // Update status
    if (statusEl) statusEl.textContent = 'Thinking...';

    fetch('/alice', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    }).then(function(resp) {
      return resp.json();
    }).then(function(data) {
      if (statusEl) statusEl.textContent = 'Ready';
      if (data.reply) addMessage(data.reply, 'alice');
      if (data.error) addMessage(data.error, 'alice');
      // Token transparency
      if (data.tokens) {
        var lastMsg = msgs.querySelector('.alice-msg:last-child');
        if (lastMsg) {
          var tokenDiv = document.createElement('div');
          tokenDiv.className = 'alice-token-info';
          var cost = data.tokens.estimated_cost_usd != null
            ? ' (~$' + data.tokens.estimated_cost_usd.toFixed(4) + ')'
            : '';
          tokenDiv.textContent = data.tokens.total_tokens + ' tokens' + cost;
          lastMsg.appendChild(tokenDiv);
        }
      }
    }).catch(function(err) {
      if (statusEl) statusEl.textContent = 'Ready';
      addMessage('Sorry, I could not process that request.', 'alice');
    });
  }

  function shortcut(text) {
    if (input) input.value = text;
    sendMessage();
  }

  function saveHistory() {
    try {
      var items = msgs.querySelectorAll('.alice-msg');
      var arr = [];
      items.forEach(function(m) { arr.push(m.outerHTML); });
      if (arr.length > 30) arr = arr.slice(-30);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(arr));
    } catch(e) {}
  }

  function loadHistory() {
    try {
      var stored = localStorage.getItem(HISTORY_KEY);
      if (!stored) return;
      var arr = JSON.parse(stored);
      if (!arr.length) return;
      msgs.innerHTML = '';
      arr.forEach(function(html) {
        var div = document.createElement('div');
        div.innerHTML = html;
        if (div.firstChild) msgs.appendChild(div.firstChild);
      });
    } catch(e) {}
  }

  // Expose to App namespace
  window._alice = {
    init: init,
    toggle: toggle,
    sendMessage: sendMessage,
    shortcut: shortcut,
    addMessage: addMessage,
  };

  // Init when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
