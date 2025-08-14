import { getOrCreateKeypair } from './e2ee.js';

window.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('signup-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    try {
      const { publicKeyBase64 } = await getOrCreateKeypair();
      document.getElementById('public_key').value = publicKeyBase64;
      form.submit();
    } catch (err) {
      alert("Failed to generate encryption keys. Please try again.");
      console.error("ECC key error:", err);
    }
  });
});
