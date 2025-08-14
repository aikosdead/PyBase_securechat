import * as E2EE from './e2ee.js';

(async () => {
  await E2EE.getOrCreateKeypair();

  const form = document.getElementById('chat-form');
  const input = document.getElementById('message-input');
  const metaRecKey = document.querySelector('meta[name="recipient-pubkey"]');
  const metaRecFmt = document.querySelector('meta[name="recipient-pub-format"]');
  const metaCsrf = document.querySelector('meta[name="csrf-token"]');
  const otherId = document.getElementById('recipient-public-key')?.dataset?.uid;
  const currentUserId = document.getElementById('current-user-id')?.value;
  const container = document.getElementById('chat-messages');

  if (!metaRecKey || !metaCsrf || !otherId || !currentUserId || !container) {
    console.error('Missing required metadata or DOM elements');
    return;
  }

  const recipientPubKey = metaRecKey.getAttribute('content') || '';
  const recipientFmt = metaRecFmt?.getAttribute('content') || 'curve25519_base64';
  if (recipientFmt !== 'curve25519_base64') {
    console.warn('Unexpected recipient key format:', recipientFmt);
  }

  // 🧱 Reusable Message Renderer
  function renderMessage({ text, sender, timestamp, isSent }) {
    const bubble = document.createElement('div');
    bubble.classList.add('message', isSent ? 'message-sent' : 'message-received');

    const meta = document.createElement('div');
    meta.classList.add('message-meta');

    const nameSpan = document.createElement('span');
    nameSpan.classList.add('sender-name');
    nameSpan.textContent = sender;

    const timeSpan = document.createElement('span');
    timeSpan.classList.add('timestamp');
    timeSpan.textContent = timestamp;

    const body = document.createElement('div');
    body.classList.add('message-body');
    body.textContent = text;

    meta.appendChild(nameSpan);
    meta.appendChild(timeSpan);
    bubble.appendChild(meta);
    bubble.appendChild(body);
    container.appendChild(bubble);
  }

  // 🔄 Message Sending
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;

    try {
      const enc = await E2EE.encryptForRecipient(msg, recipientPubKey);

      const res = await fetch(`/auth/chat/${otherId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': metaCsrf.getAttribute('content')
        },
        credentials: 'include',
        body: JSON.stringify(enc)
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Send failed: ${res.status} ${txt}`);
      }

      // ✅ Append sent message immediately
      const now = new Date();
      const formatted = now.toLocaleString('en-US', {
        timeZone: 'Asia/Manila',
        month: 'short', day: 'numeric',
        hour: 'numeric', minute: '2-digit',
        hour12: true
      });

      renderMessage({
        text: msg,
        sender: 'You',
        timestamp: formatted,
        isSent: true
      });

      container.scrollTop = container.scrollHeight;
      input.value = '';
    } catch (err) {
      console.error('Encryption or sending failed:', err);
      alert('Failed to send encrypted message: ' + err.message);
    }
  });

  // 🧩 Message Rendering
  const rawMessages = document.getElementById('encrypted-messages')?.textContent;
  if (!rawMessages) {
    console.warn('No messages found in #encrypted-messages');
    return;
  }

  let messages = [];
  try {
    messages = JSON.parse(rawMessages);
  } catch (err) {
    console.error('Failed to parse encrypted messages JSON:', err);
    return;
  }

  for (const msg of messages) {
    try {
      const decrypted = await E2EE.decryptMessage(msg);
      if (!decrypted) continue;

      const isSent = msg.from === currentUserId;
      const senderName = isSent ? 'You' : document.querySelector('.chat-header strong')?.textContent || 'Unknown';

      const ts = msg.timestamp ? new Date(msg.timestamp) : null;
      const formatted = ts
        ? ts.toLocaleString('en-US', {
            timeZone: 'Asia/Manila',
            month: 'short', day: 'numeric',
            hour: 'numeric', minute: '2-digit',
            hour12: true
          })
        : 'Unknown time';

      renderMessage({
        text: decrypted,
        sender: senderName,
        timestamp: formatted,
        isSent
      });
    } catch (err) {
      console.warn('Failed to decrypt message:', msg, err);
    }
  }

  // ✅ Auto-scroll to bottom
  container.scrollTop = container.scrollHeight;
})();
