from Crypto.PublicKey import ECC
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
import base64

def generate_ecc_keypair():
    key = ECC.generate(curve='P-256')
    private_key = key.export_key(format='PEM')
    public_key = key.public_key().export_key(format='PEM')
    return private_key, public_key

def derive_shared_key(private_key_pem, peer_public_key_pem):
    priv_key = ECC.import_key(private_key_pem)
    pub_key = ECC.import_key(peer_public_key_pem)
    shared_point = priv_key.d * pub_key.pointQ  # ECDH
    x_bytes = int(shared_point.x).to_bytes(32, byteorder='big')
    return SHA256.new(x_bytes).digest()

def encrypt_with_shared_key(plain_text, shared_key):
    nonce = get_random_bytes(16)
    cipher = AES.new(shared_key, AES.MODE_EAX, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plain_text.encode())
    return base64.b64encode(nonce + tag + ciphertext).decode()

def decrypt_with_shared_key(encrypted_text, shared_key):
    raw = base64.b64decode(encrypted_text)
    nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(shared_key, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode()
