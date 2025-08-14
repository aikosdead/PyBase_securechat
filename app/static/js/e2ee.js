// app/static/js/e2ee.js
// TweetNaCl helpers (Curve25519). Public key: base64. Private key kept in IndexedDB.

const DB_NAME = 'securechat-kv';
const STORE = 'kv';

// --- IndexedDB KV store ---
function idbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbGet(key) {
  const db = await idbOpen();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const req = tx.objectStore(STORE).get(key);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

async function idbSet(key, val) {
  const db = await idbOpen();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    const req = tx.objectStore(STORE).put(val, key);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}

// --- Base64 helpers ---
function b64encode(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function b64decode(str) {
  const bin = atob(str);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// --- Keypair management ---
export async function generateKeyPair() {
  const kp = nacl.box.keyPair(); // Curve25519
  const pubB64 = b64encode(kp.publicKey);
  await idbSet('pub', pubB64);
  await idbSet('priv', kp.secretKey);
  return { publicKeyBase64: pubB64, privateKey: kp.secretKey };
}

export async function getOrCreateKeypair() {
  let pub = await idbGet('pub');
  let priv = await idbGet('priv');
  if (pub && priv) {
    return { publicKeyBase64: pub, privateKey: priv };
  }
  return await generateKeyPair();
}

export async function getPrivateKey() {
  let priv = await idbGet('priv');
  if (!priv) {
    const kp = await getOrCreateKeypair();
    priv = kp.privateKey;
  }
  return priv;
}

// --- Encryption ---
export async function encryptForRecipient(plaintext, recipientPublicBase64) {
  const priv = await getPrivateKey();
  const myPubB64 = await idbGet('pub');
  const recipientPub = b64decode(recipientPublicBase64);
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);

  const shared = nacl.box.before(recipientPub, priv);
  const ct = nacl.secretbox(new TextEncoder().encode(plaintext), nonce, shared);

  return {
    ciphertext: b64encode(ct),
    nonce: b64encode(nonce),
    sender_pub: myPubB64,
    scheme: 'nacl-secretbox-x25519'
  };
}

// --- Decryption ---
export async function decryptFromSender(ciphertextB64, nonceB64, senderPubB64) {
  const priv = await getPrivateKey();
  const senderPub = b64decode(senderPubB64);
  const shared = nacl.box.before(senderPub, priv);
  const nonce = b64decode(nonceB64);
  const ct = b64decode(ciphertextB64);
  const pt = nacl.secretbox.open(ct, nonce, shared);
  if (!pt) return null;
  return new TextDecoder().decode(pt);
}

export async function decryptMessage(msg) {
  const { ciphertext, nonce, sender_pub } = msg;

  if (!ciphertext || !nonce || !sender_pub) {
    console.warn('Missing fields in message:', msg);
    return null;
  }

  try {
    return await decryptFromSender(ciphertext, nonce, sender_pub);
  } catch (err) {
    console.error('Decryption failed:', err);
    return null;
  }
}
