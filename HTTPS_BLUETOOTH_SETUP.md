# HTTPS/SSL Setup Guide for Mobile Bluetooth Printing

## Why HTTPS is Required

**Web Bluetooth API requires HTTPS** - Browsers block Bluetooth access on non-secure (HTTP) connections for security reasons. To enable mobile Bluetooth printing, you **must** run the server with HTTPS/SSL enabled.

## Quick Start (Development)

### 1. Generate SSL Certificate

```powershell
# Run the certificate generator
python generate_cert.py
```

This creates:
- `cert.pem` - SSL certificate
- `key.pem` - Private key

### 2. Start HTTPS Server

**Option A: Using PowerShell Script (Recommended)**
```powershell
.\run_https.ps1
```

**Option B: Manual Command**
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run with HTTPS
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
```

### 3. Access the Application

The server will be available at:
- `https://192.168.1.4:8000` (your local IP - **use this for mobile**)
- `https://localhost:8000` (desktop only)
- `https://127.0.0.1:8000` (desktop only)

## Mobile Device Setup

### Step 1: Accept the Self-Signed Certificate

When you first access the app on your mobile device:

1. Open Chrome/Edge browser on your mobile
2. Navigate to `https://192.168.1.4:8000`
3. You'll see a security warning:
   - **Chrome**: "Your connection is not private"
   - Tap **"Advanced"**
   - Tap **"Proceed to 192.168.1.4 (unsafe)"**
4. The site will load and the certificate is now trusted for this session

### Step 2: Install as PWA (Optional but Recommended)

For the best experience:

1. After accepting the certificate, tap the **menu (⋮)** in Chrome
2. Select **"Add to Home Screen"** or **"Install App"**
3. Name it "Zergo Sales" or similar
4. Tap **"Add"**
5. The app icon appears on your home screen
6. Launch from home screen - it runs like a native app!

### Step 3: Test Bluetooth Printing

1. Navigate to any bill (e.g., `/sales/25/`)
2. Tap the orange **"Mobile Print (Bluetooth)"** button
3. Tap **"Print via Bluetooth"**
4. Turn on your Bluetooth printer
5. Select your printer from the list
6. The bill prints automatically!

## Supported Bluetooth Printers

The system supports most ESC/POS thermal printers:

### Popular Models:
- **GOOJPRT** PT-210, MTP-II, MTP-III
- **Bluetooth Printer** 58mm/80mm
- **POS-5802** / POS-8002
- **RPP-300** / RPP-320
- **Munbyn** portable printers
- **Phomemo** M02/M02S
- **Any ESC/POS compatible** Bluetooth printer

### Printer Requirements:
- ✓ Bluetooth connectivity (BLE or Classic)
- ✓ ESC/POS command support
- ✓ Paper: 58mm or 80mm thermal paper
- ✓ Charged battery (for portable printers)

## Troubleshooting

### Issue: "Bluetooth not supported"

**Solution:**
- Use Chrome or Edge browser (Safari doesn't support Web Bluetooth)
- Ensure you're using HTTPS (not HTTP)
- Check that Bluetooth is enabled on your device

### Issue: "No printer found"

**Solution:**
1. Turn on your Bluetooth printer
2. Put printer in pairing mode (usually auto-enabled)
3. Make sure printer is not connected to another device
4. Try scanning again
5. Check printer battery level

### Issue: "Security warning" on every visit

**Solution:**

**Permanent Trust (Android Chrome):**
1. Open Chrome browser
2. Go to `chrome://flags`
3. Search for "insecure origins"
4. Add `https://192.168.1.4:8000` to allowed origins
5. Restart browser

**Alternative: Use localhost.run (Temporary Public URL)**
```powershell
# In a new terminal, create a tunnel
ssh -R 80:localhost:8000 nokey@localhost.run
```
This gives you a real HTTPS URL (e.g., `https://random-name.localhost.run`)

### Issue: Certificate expired

**Solution:**
```powershell
# Regenerate certificate (valid for 1 year)
python generate_cert.py

# Restart server
.\run_https.ps1
```

### Issue: "ERR_CERT_AUTHORITY_INVALID"

This is **normal** for self-signed certificates. Just click:
- **Advanced** → **Proceed to site (unsafe)**

For production, you would use a real SSL certificate from Let's Encrypt or a Certificate Authority.

## Network Access (Same WiFi Required)

### Find Your IP Address

**Windows:**
```powershell
ipconfig
# Look for "IPv4 Address" under your WiFi adapter
```

**Update Certificate if IP Changed:**
```powershell
# Edit generate_cert.py and update local_ip
# Or regenerate:
python generate_cert.py
```

### Allow Firewall Access

If mobile devices can't connect:

**Windows Firewall:**
```powershell
# Add inbound rule for port 8000
New-NetFirewallRule -DisplayName "Django HTTPS" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

## Production Deployment (Optional)

For production with a real domain and SSL:

### 1. Use Let's Encrypt (Free SSL)

```bash
# Install certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com
```

### 2. Update Django Settings

```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 3. Use Nginx/Apache

Configure a reverse proxy with SSL termination for better performance.

## Print Quality Settings

### Adjust Thermal Printer Settings

Edit `templates/sales/mobile_print.html`:

```javascript
// Line 480+: Adjust font size
commands.push(GS, 0x21, 0x00); // Normal: 0x00, Double: 0x11

// Line 490+: Adjust line spacing
commands.push(ESC, 0x33, 0x30); // Default: 0x30 (48)
```

### Paper Size

Default: **80mm** thermal paper

For **58mm** paper, adjust CSS:
```css
@page {
    size: 58mm auto;
}
```

## Security Notes

### Development (Current Setup)
- ✓ Self-signed certificate (shows warning but functional)
- ✓ HTTPS enabled (required for Bluetooth)
- ✓ Local network only (192.168.x.x)
- ⚠ Not suitable for public internet

### Production Recommendations
- Use real SSL certificate (Let's Encrypt)
- Enable `SECURE_SSL_REDIRECT`
- Use environment variables for secrets
- Set up proper firewall rules
- Use a reverse proxy (Nginx/Apache)

## Testing Checklist

- [ ] Server runs with HTTPS (`https://` in URL)
- [ ] Certificate accepted on mobile
- [ ] Bluetooth printer powered on
- [ ] Mobile and server on same WiFi
- [ ] Browser supports Web Bluetooth (Chrome/Edge)
- [ ] Bill detail page loads
- [ ] "Mobile Print" button visible
- [ ] Bluetooth scan finds printer
- [ ] Print successful

## Additional Resources

- **Django SSL Setup**: https://docs.djangoproject.com/en/5.0/topics/security/
- **Web Bluetooth API**: https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API
- **ESC/POS Commands**: https://reference.epson-biz.com/modules/ref_escpos/

## Support

For issues or questions:
1. Check this guide thoroughly
2. Verify HTTPS is working (look for 🔒 in browser)
3. Test on Chrome/Edge mobile (not Safari)
4. Ensure same WiFi network
5. Check printer battery and Bluetooth status
