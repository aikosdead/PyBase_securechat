import * as E2EE from './e2ee.js';
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.5.0/firebase-app.js";
import {
  getFirestore, doc, getDoc, updateDoc, arrayUnion, arrayRemove, collection, query, where, getDocs
} from "https://www.gstatic.com/firebasejs/10.5.0/firebase-firestore.js";

const firebaseConfig = window.firebaseConfig;
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

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
  const ephemeralToggle = document.getElementById('ephemeral-toggle');
const expirySelector = document.getElementById('expiry-selector');

ephemeralToggle.addEventListener('change', () => {
  expirySelector.style.display = ephemeralToggle.checked ? 'block' : 'none';
});

  const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  if (!metaRecKey || !metaCsrf || !otherId || !currentUserId || !container) {
    console.error('Missing required metadata or DOM elements');
    return;
  }

  const recipientPubKey = metaRecKey.getAttribute('content') || '';
  const recipientFmt = metaRecFmt?.getAttribute('content') || 'curve25519_base64';
  if (recipientFmt !== 'curve25519_base64') {
    console.warn('Unexpected recipient key format:', recipientFmt);
  }

  function formatTimestamp(ts) {
    if (!ts) return 'Unknown time';
  
    const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  
    let date;
    try {
      if (ts.toDate) {
        date = ts.toDate(); // Firestore Timestamp
      } else if (ts instanceof Date) {
        date = ts;
      } else if (typeof ts === 'string') {
        const safeTs = ts.endsWith('Z') ? ts : ts + 'Z';
        date = new Date(safeTs);
      } else if (typeof ts === 'number') {
        date = new Date(ts); // Unix timestamp
      } else {
        throw new RangeError('Unrecognized timestamp format');
      }
  
      if (isNaN(date.getTime())) throw new RangeError('Invalid time value');
    } catch (err) {
      console.warn('formatTimestamp failed:', ts, err);
      return 'Invalid time';
    }
  
    return new Intl.DateTimeFormat('en-US', {
      timeZone: userTimeZone,
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }).format(date);
  }
  
  // 🧱 Reusable Message Renderer
  function renderMessage({ text, sender, timestamp, isSent, senderUid, avatarUrl, ephemeral = false, expiresAt = null }) {
    const bubble = document.createElement('div');
    bubble.classList.add('message', isSent ? 'message-sent' : 'message-received');
  
    const meta = document.createElement('div');
    meta.classList.add('message-meta');
  
    const avatar = document.createElement('img');
    avatar.classList.add('user-avatar');
    avatar.setAttribute('data-uid', senderUid);
    avatar.src = avatarUrl || '/static/img/default-avatar.png';
    avatar.alt = `${sender}'s avatar`;
    avatar.width = 32;
    avatar.height = 32;
    avatar.style.borderRadius = '50%';
    avatar.style.marginRight = '8px';
  
    const nameSpan = document.createElement('span');
    nameSpan.classList.add('username');
    nameSpan.setAttribute('data-uid', senderUid);
    nameSpan.textContent = sender;
  
    const timeSpan = document.createElement('span');
    timeSpan.classList.add('timestamp');
    timeSpan.textContent = timestamp;
  
    const body = document.createElement('div');
    body.classList.add('message-body');
    body.textContent = text;
  
    meta.appendChild(avatar);
    meta.appendChild(nameSpan);
    meta.appendChild(timeSpan);
    bubble.appendChild(meta);
    bubble.appendChild(body);
  
    // 🔥 Ephemeral countdown
    if (ephemeral && expiresAt) {
      const countdown = document.createElement('div');
      countdown.className = 'text-danger small';
      bubble.appendChild(countdown);
  
      const updateCountdown = () => {
        const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
        countdown.textContent = `🔥 Expires in ${remaining}s`;
  
        if (remaining <= 0) {
          bubble.classList.add('fade-out');
          setTimeout(() => bubble.remove(), 1000); // fade then remove
          clearInterval(timer);
        }
      };
  
      updateCountdown();
      const timer = setInterval(updateCountdown, 1000);
    }
  
    container.appendChild(bubble);
  }    

  // 🔄 Message Sending
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;

  try {
    const enc = await E2EE.encryptForRecipient(msg, recipientPubKey);

const isEphemeral = ephemeralToggle.checked;
const expirySeconds = parseInt(document.getElementById('expiry-seconds')?.value || '10', 10);
const now = Date.now();
const expiresAt = isEphemeral ? now + expirySeconds * 1000 : null;

const messagePayload = {
  ...enc,
  sender: currentUserId,
  timestamp: now,
  ephemeral: isEphemeral,
  expiresAt
};

// ✅ Use dynamic endpoint injected from Flask
const chatEndpoint = document.getElementById('chat-endpoint').value;

const res = await fetch(chatEndpoint, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': metaCsrf.getAttribute('content')
  },
  credentials: 'include',
  body: JSON.stringify(messagePayload)
});

if (!res.ok) {
  const txt = await res.text();
  throw new Error(`Send failed: ${res.status} ${txt}`);
}

const formatted = formatTimestamp(now);
renderMessage({
  text: msg,
  sender: 'You',
  timestamp: formatted,
  isSent: true,
  ephemeral: isEphemeral,
  expiresAt
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
  
      console.log('Raw timestamp:', msg.timestamp);  // ✅ Step 1: log raw value
  
      const formatted = formatTimestamp(msg.timestamp);  // ✅ Step 2: format it
  
      const expiresAt = msg.ephemeral && msg.expiresAt ? new Date(msg.expiresAt).getTime() : null;

renderMessage({
  text: decrypted,
  sender: senderName,
  timestamp: formatted,
  isSent,
  senderUid: msg.from,
  avatarUrl: msg.avatar_url || '/static/img/default-avatar.png',
  ephemeral: msg.ephemeral || false,
  expiresAt
});

    } catch (err) {
      console.warn('Failed to decrypt message:', msg, err);
    }
  }  

  // ✅ Auto-scroll to bottom
  container.scrollTop = container.scrollHeight;
})();

async function showProfilePopout(uid, anchorEl) {
  console.log("Popout triggered for UID:", uid);

  const q = query(collection(db, "usernames"), where("uid", "==", uid));
  const querySnapshot = await getDocs(q);

  if (querySnapshot.empty) {
    console.warn("No username found for UID:", uid);
    return;
  }

  const doc = querySnapshot.docs[0];
  const username = doc.id;
  const photo_url = doc.data().photo_url || "/static/img/default-avatar.png";

  const popout = document.createElement("div");
  popout.classList.add("profile-popout");
  popout.innerHTML = `
    <button class="close-popout" style="float:right;">×</button>
    <img src="${photo_url}" alt="${username}'s avatar" />
    <h3>${username}</h3>
    <button class="add-friend" data-uid="${uid}">Add Friend</button>
    <button class="block-user" data-uid="${uid}">Block</button>
    <button class="call-user" data-uid="${uid}">Call</button>
    <button class="video-call-user" data-uid="${uid}">Video Call</button>
  `;

  popout.querySelector(".close-popout").addEventListener("click", () => {
    popout.remove();
  });
  
  // 🧭 Anchor near the clicked element
if (anchorEl) {
  const rect = anchorEl.getBoundingClientRect();
  const headerRect = document.querySelector('.chat-header').getBoundingClientRect();

  const top = rect.bottom - headerRect.top + 10;
  const left = rect.left - headerRect.left;

  popout.style.setProperty('--popout-top', `${top}px`);
  popout.style.setProperty('--popout-left', `${left}px`);
} else {
  // Fallback position
  popout.style.setProperty('--popout-top', '100px');
  popout.style.setProperty('--popout-left', '100px');
}

  // 🧹 Remove existing popouts
  document.querySelectorAll(".profile-popout").forEach(el => el.remove());

  document.querySelector('.chat-header').appendChild(popout);

  requestAnimationFrame(() => {
    setTimeout(() => {
      popout.classList.add('show');
    }, 100);
  });  
}
const chatContainer = document.getElementById('chat-messages');

chatContainer.addEventListener("click", async (e) => {
const target = e.target.closest(".user-avatar, .username");
if (!target) return;

const uid = target.dataset.uid;
if (!uid) return;

showProfilePopout(uid, target);
});

document.body.addEventListener("click", (e) => {
  const uid = e.target.dataset.uid;
  if (!uid) return;

  if (e.target.classList.contains("add-friend")) {
    addFriend(uid);
  } else if (e.target.classList.contains("block-user")) {
    blockUser(uid);
  } else if (e.target.classList.contains("call-user")) {
    startCall(uid);
  } else if (e.target.classList.contains("video-call-user")) {
    startVideoCall(uid);
  }
});

document.addEventListener("click", (e) => {
  const isPopout = e.target.closest(".profile-popout");
  const isTrigger = e.target.closest(".user-avatar, .username");
  if (!isPopout && !isTrigger) {
    document.querySelectorAll(".profile-popout").forEach(el => el.remove());
  }
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".profile-trigger").forEach(trigger => {
    trigger.addEventListener("click", (e) => {
      e.preventDefault(); // ✅ Prevents navigation
      const uid = e.currentTarget.dataset.uid;
      if (uid) showProfilePopout(uid, e.currentTarget);
    });
  });
});

function addFriend(uid) {
  console.log("Add friend:", uid);
  // TODO: Firestore write to profiles/{currentUserId}/friends
}

function blockUser(uid) {
  console.log("Block user:", uid);
  // TODO: Firestore write to profiles/{currentUserId}/blocked
}

function startCall(uid) {
  console.log("Start call with:", uid);
  // TODO: Trigger signaling logic
}

function startVideoCall(uid) {
  console.log("Start video call with:", uid);
  // TODO: Trigger video signaling logic
}
