/* ══════════════════════════════════════════════════════════════
   JARVIS Web UI — Frontend Logic (WebSocket + Markdown + API)
   ══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const btnSend = document.getElementById('btnSend');
  const providerSelect = document.getElementById('providerSelect');

  let ws = null;
  let currentAssistantBubble = null;
  let currentAssistantRaw = '';

  // 1. Connect WebSocket
  function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected to JARVIS');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'start') {
        currentAssistantBubble = createMessageRow('jarvis', '');
        currentAssistantRaw = '';
      } else if (data.type === 'tool_call') {
        renderToolBadge(data.tool, data.args);
      } else if (data.type === 'content') {
        if (!currentAssistantBubble) {
          currentAssistantBubble = createMessageRow('jarvis', '');
        }
        currentAssistantRaw += data.content;
        currentAssistantBubble.innerHTML = parseMarkdown(currentAssistantRaw);
        scrollToBottom();
      } else if (data.type === 'error') {
        createMessageRow('jarvis', `⚠️ **Error**: ${data.message}`);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed. Reconnecting in 3s...');
      setTimeout(initWebSocket, 3000);
    };
  }

  const modelSelect = document.getElementById('modelSelect');

  // 2. Load Config & Providers & Models
  async function loadProviders() {
    try {
      const res = await fetch('/api/config/providers');
      const providers = await res.json();

      providerSelect.innerHTML = '';
      providers.forEach((p) => {
        const opt = document.createElement('option');
        opt.value = p.name;
        opt.textContent = `${p.display_name} (${p.protocol})`;
        providerSelect.appendChild(opt);
      });

      // Load active config
      const cfgRes = await fetch('/api/config');
      const cfg = await cfgRes.json();
      if (cfg.provider && cfg.provider.active) {
        providerSelect.value = cfg.provider.active;
        await loadModels(cfg.provider.active, cfg.provider.model);
      }
    } catch (e) {
      console.error('Failed to load providers:', e);
    }
  }

  async function loadModels(providerName, activeModelId = null) {
    if (!modelSelect) return;
    modelSelect.innerHTML = '<option value="">Fetching live models...</option>';
    try {
      const res = await fetch(`/api/config/models?provider=${encodeURIComponent(providerName)}`);
      const models = await res.json();

      modelSelect.innerHTML = '';
      if (!models || models.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'No models available';
        modelSelect.appendChild(opt);
        return;
      }

      models.forEach((m) => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.name ? `${m.id} (${m.name})` : m.id;
        modelSelect.appendChild(opt);
      });

      if (activeModelId && models.some((m) => m.id === activeModelId)) {
        modelSelect.value = activeModelId;
      }
    } catch (e) {
      console.error('Failed to load models:', e);
      modelSelect.innerHTML = '<option value="">Error fetching models</option>';
    }
  }

  // 3. Provider & Model Switch Handlers
  providerSelect.addEventListener('change', async () => {
    const selectedProvider = providerSelect.value;
    try {
      await fetch('/api/config/provider', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: selectedProvider }),
      });
      createMessageRow('jarvis', `Switched active provider to **${selectedProvider}**.`);
      await loadModels(selectedProvider);
    } catch (e) {
      console.error('Failed to switch provider:', e);
    }
  });

  if (modelSelect) {
    modelSelect.addEventListener('change', async () => {
      const selectedProvider = providerSelect.value;
      const selectedModel = modelSelect.value;
      if (!selectedModel) return;
      try {
        await fetch('/api/config/provider', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: selectedProvider, model: selectedModel }),
        });
        createMessageRow('jarvis', `Switched active model to **${selectedModel}**.`);
      } catch (e) {
        console.error('Failed to switch model:', e);
      }
    });
  }

  // 4. Send Message Handler
  function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    createMessageRow('user', text);
    ws.send(JSON.stringify({ message: text }));

    chatInput.value = '';
    chatInput.focus();
    scrollToBottom();
  }

  btnSend.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 5. Helper Functions
  function createMessageRow(role, text) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = parseMarkdown(text);

    row.appendChild(avatar);
    row.appendChild(bubble);

    chatMessages.appendChild(row);
    scrollToBottom();
    return bubble;
  }

  function renderToolBadge(toolName, toolArgs) {
    const badge = document.createElement('div');
    badge.className = 'tool-badge';
    badge.innerHTML = `🛠 Executing tool: <strong>${toolName}</strong> (${JSON.stringify(toolArgs)})`;
    chatMessages.appendChild(badge);
    scrollToBottom();
  }

  function parseMarkdown(text) {
    if (!text) return '';
    // Handle thinking tags: <think...>...</think...> or unclosed <think...>
    let parsed = text.replace(
      /<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>([\s\S]*?)(?:<\/(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>|$)/gi,
      (match, thought) => {
        const trimmed = thought.trim();
        if (!trimmed) return '';
        return `<details class="thought-box"><summary class="thought-summary">💭 Thought</summary><div class="thought-content">${trimmed}</div></details>`;
      }
    );

    // Simple markdown parsing
    return parsed
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Initialize
  initWebSocket();
  loadProviders();
});
