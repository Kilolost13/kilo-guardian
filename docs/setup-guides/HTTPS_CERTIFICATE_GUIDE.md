# Kilo HTTPS Certificate Installation Guide

## Current Status
✅ HTTPS is now active on https://192.168.68.61/
✅ Self-signed certificate created and installed
✅ Camera access will work once certificate is trusted

## How to Install Certificate on Android Tablet

### Method 1: Download and Install (Easiest)
1. On the tablet, open Chrome browser
2. Navigate to: **http://192.168.68.61:8080/cert/kilo.crt**
3. The certificate will download
4. Go to Settings → Security → Encryption & credentials → Install a certificate
5. Choose "CA certificate" 
6. Select the downloaded `kilo.crt` file
7. Name it "Kilo Server" when prompted
8. Now navigate to **https://192.168.68.61/** - no warning!

### Method 2: Accept Browser Warning (Quick but less secure)
1. Navigate to https://192.168.68.61/
2. You'll see "Your connection is not private" 
3. Tap "Advanced"
4. Tap "Proceed to 192.168.68.61 (unsafe)"
5. The site will load and camera will work
6. Note: You may need to do this periodically

### Method 3: Copy from Desktop
The certificate file is also saved at:
- `/home/kilo/Desktop/kilo-certificate.crt`

You can transfer this to the tablet via USB or network and install it.

## Why HTTPS is Needed
Modern browsers (Chrome/Firefox) require HTTPS to access:
- Camera/webcam
- Microphone  
- Geolocation
- Other sensitive sensors

Without HTTPS, the browser blocks camera access for security reasons.

## Certificate Details
- Type: Self-signed X.509 certificate
- Valid for: 1 year (until Jan 16, 2027)
- Subject: CN=kilo.local, O=Kilo
- Key: RSA 2048-bit
- Located: /etc/nginx/ssl/kilo.crt

## Testing
After installing the certificate, test camera access at:
https://192.168.68.61/

The browser should show a lock icon 🔒 and camera should be accessible.

## Troubleshooting
- **Still seeing warning**: Make sure you installed as "CA certificate" not "User certificate"
- **Camera not working**: Check browser permissions in Settings → Apps → Chrome → Permissions
- **Certificate expired**: Regenerate with the command in this directory
- **Wrong hostname**: Certificate is for kilo.local and 192.168.68.61

## Future: Production Certificate
For a production setup, consider:
1. Getting a real domain name
2. Using Let's Encrypt for free, trusted certificates
3. Setting up automatic certificate renewal
