# Browser Cache Clearing Guide - Settlement Status UI Update

## Issue: Bills Management Page Still Shows Old Labels

The Bills Management page may still display "Unpaid", "Partial", "Paid" even after the settlement status migration is complete. This is due to **browser caching**.

## Root Cause
Modern browsers cache HTML templates, CSS, and JavaScript files to improve performance. When templates are updated on the server, browsers may continue showing cached (old) versions.

## Solution: Clear Browser Cache

### Google Chrome / Microsoft Edge
1. **Hard Refresh** (Recommended - Quick Fix):
   - Press `Ctrl + Shift + R` (Windows/Linux)
   - Or `Ctrl + F5`
   - Or `Shift + F5`

2. **Manual Cache Clear** (Thorough):
   - Press `Ctrl + Shift + Delete`
   - Select "Cached images and files"
   - Click "Clear data"
   - Refresh the page (`F5`)

3. **Developer Tools Method**:
   - Press `F12` to open Developer Tools
   - Right-click the refresh button
   - Select "Empty Cache and Hard Reload"

### Firefox
1. **Hard Refresh**:
   - Press `Ctrl + Shift + R` (Windows/Linux)
   - Or `Ctrl + F5`

2. **Manual Cache Clear**:
   - Press `Ctrl + Shift + Delete`
   - Check "Cache"
   - Click "Clear"
   - Refresh the page

### Safari (Mac)
1. **Hard Refresh**:
   - Press `Cmd + Option + R`

2. **Manual Cache Clear**:
   - Safari menu → Preferences
   - Advanced tab → Check "Show Develop menu"
   - Develop menu → Empty Caches
   - Refresh the page

## Verification Steps

After clearing cache, verify the Bills Management page shows:

### ✅ Expected UI Labels

**Filter Tabs (Top of page)**:
- ❌ OLD: `Unpaid | Partial | Paid`
- ✅ NEW: `Unsettled | Partially Settled | Settled`

**Table Column Header**:
- ❌ OLD: `Payment`
- ✅ NEW: `Settlement`

**Status Badges (in table rows)**:
- ❌ OLD: Red badge "UNPAID", Yellow badge "PARTIAL", Green badge "PAID"
- ✅ NEW: Red badge "UNSETTLED", Yellow badge "PARTIALLY SETTLED", Green badge "SETTLED"

## Still Not Working?

If the page still shows old labels after clearing cache:

### 1. Check Django Server Status
```powershell
# Stop the server (in terminal where it's running)
Ctrl + C

# Restart the server
.\venv\Scripts\python.exe manage.py runserver
```

### 2. Verify Template File
```powershell
# Run verification script
python verify_ui_changes.py
```

Expected output: All checks show ✓

### 3. Check Browser Developer Console
- Press `F12` to open Developer Tools
- Go to "Console" tab
- Look for any JavaScript errors
- Go to "Network" tab
- Refresh page
- Check if HTML responses are showing "(from cache)" or fresh

### 4. Try Incognito/Private Mode
- Open new Incognito/Private window
- Navigate to: `http://127.0.0.1:8000/sales/`
- Incognito mode doesn't use cached files

### 5. Different Browser
- Try opening the page in a different browser
- If it works there, confirm it's a cache issue in original browser

## Django Template Cache (Advanced)

Django may also cache templates in production. If using production settings:

```python
# In settings.py, ensure template caching is disabled during development
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
                # For development, use non-cached loaders
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]
```

## Mobile Device Cache

If accessing from mobile browser:

### Android Chrome
1. Chrome menu → Settings → Privacy → Clear browsing data
2. Select "Cached images and files"
3. Tap "Clear data"

### iOS Safari
1. Settings → Safari → Clear History and Website Data
2. Confirm

## Summary

**Most Common Solution**: 
- Press `Ctrl + Shift + R` (or `Cmd + Option + R` on Mac)
- This hard refresh bypasses cache and loads fresh content

**Verification URL**: 
- Navigate to: `http://127.0.0.1:8000/sales/`
- Check that all filter tabs and labels show new "Settlement" terminology

**All Template Changes Verified**: ✅
- Filter tabs: Updated ✓
- Table header: Updated ✓
- Desktop badges: Updated ✓
- Mobile badges: Updated ✓
- Old terminology removed: Confirmed ✓
