#!/usr/bin/env python
"""Generate self-signed SSL certificate for development"""

from OpenSSL import crypto
import os
import socket

def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.1.4"

def generate_self_signed_cert(cert_file="cert.pem", key_file="key.pem"):
    """Generate a self-signed certificate with multiple SANs"""
    
    local_ip = get_local_ip()
    
    # Create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)
    
    # Create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "LK"  # Sri Lanka
    cert.get_subject().ST = "Western"
    cert.get_subject().L = "Colombo"
    cert.get_subject().O = "Zergo Distributors"
    cert.get_subject().OU = "Sales & Distribution"
    cert.get_subject().CN = local_ip
    
    # Add Subject Alternative Names (SAN) for all possible access points
    san_list = [
        f"IP:{local_ip}",
        "IP:127.0.0.1",
        "IP:0.0.0.0",
        "DNS:localhost",
        "DNS:*.localhost",
    ]
    
    # Add common private IP ranges
    san_list.extend([
        "IP:192.168.1.4",
        "IP:192.168.0.1",
        "IP:10.0.0.1",
    ])
    
    san_string = ",".join(san_list)
    
    cert.add_extensions([
        crypto.X509Extension(b"subjectAltName", False, san_string.encode()),
        crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE"),
        crypto.X509Extension(b"keyUsage", True, b"digitalSignature, keyEncipherment, keyCertSign"),
        crypto.X509Extension(b"extendedKeyUsage", False, b"serverAuth"),
    ])
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for 1 year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')
    
    # Save certificate
    with open(cert_file, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    # Save private key
    with open(key_file, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         SSL CERTIFICATE GENERATED SUCCESSFULLY            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n✓ Certificate: {cert_file}")
    print(f"✓ Private Key: {key_file}")
    print(f"✓ Valid for: 1 year")
    print(f"✓ Primary IP: {local_ip}")
    print(f"\nSupported Addresses:")
    print(f"  • https://{local_ip}:8000")
    print(f"  • https://localhost:8000")
    print(f"  • https://127.0.0.1:8000")
    print(f"  • https://192.168.1.4:8000")
    print(f"\n⚠ Browser Security Warning:")
    print(f"  Self-signed certificates will show a warning.")
    print(f"  Click 'Advanced' → 'Proceed to site' to continue.")
    print(f"\n📱 For Mobile Bluetooth Printing:")
    print(f"  HTTPS is required for Web Bluetooth API!")
    print("════════════════════════════════════════════════════════════")

if __name__ == "__main__":
    generate_self_signed_cert()

