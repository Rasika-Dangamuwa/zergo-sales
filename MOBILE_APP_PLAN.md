# Mobile App Plan — Zergo Distributors Sales App

## Background & Problem

Field sales reps work in rural areas with no internet. They need to:
- Create bills at shops
- Process returns and exchanges
- Print receipts via Bluetooth (Gooiprint PT-210)
- Sync data when back in range

The current system is a Django web app (multi-tenant, subdomain-based).
Web browsers on iOS block Web Bluetooth API (Apple forces all iOS browsers
to use WebKit which does not support Web Bluetooth). So a pure PWA will not work.

---

## Printer

**All reps use: Gooiprint PT-210**
- Bluetooth Low Energy (BLE)
- Thermal receipt printer
- Web Bluetooth API works on Android Chrome but NOT on iOS (any browser)

---

## Two-Phase Plan

---

## Phase 1 — Android WebView APK (Quick Solution)

### What it is
Wrap the existing Django web app inside an Android WebView app.
The app opens `http://zergo001.zergosales.com` inside a native shell.

### Why
- Zero new backend work — uses the existing web app as-is
- Bluetooth printing works via WebView's access to Android BLE
- Can be installed on Android phones without Play Store (APK sideload)
- Can be built quickly (days, not months)

### How it works
1. Build a simple Android app (Kotlin or using Capacitor/Cordova)
2. Load the existing web URL inside a WebView
3. Inject a JavaScript bridge for Bluetooth printing
4. The web app detects it's inside the WebView and enables Bluetooth print button
5. App stores auth session just like a browser

### Multi-tenant handling
- Each tenant gets the app configured with their subdomain
- OR one app with a login screen that asks for tenant subdomain
- App saves the subdomain in local storage and always opens that tenant's URL

### Limitations
- **Requires internet** — WebView just loads the web app, no offline support
- **Android only** — iOS blocks WebView Bluetooth too (same WebKit restriction)
- Not available on iOS at all in Phase 1

### Tools to build
- Android Studio (Kotlin) — for WebView shell + Bluetooth bridge
- OR Capacitor (wraps web app, easier) with Android target

---

## Phase 2 — React Native App (Full Offline Solution)

### What it is
A proper native mobile app built with React Native, talking to a new
Django REST API backend.

### Why
- Works fully offline — stores data in local SQLite
- Syncs when internet is available
- Works on both Android and iOS (React Native covers both)
- Bluetooth printing works via native BLE on both platforms
- Full control over the offline experience

### How it works

#### Frontend (React Native)
- Local SQLite database on the phone (via expo-sqlite or WatermelonDB)
- Rep creates bills, returns, exchanges — all saved locally first
- When online: syncs to Django server via REST API
- Bluetooth printing via react-native-ble-plx or expo-bluetooth

#### Backend (Django REST API)
- Add Django REST Framework to existing project
- New API endpoints for: bills, returns, exchanges, shops, products, settlements
- Token-based auth (DRF TokenAuth or JWT)
- Sync endpoints: upload offline queue, download master data (products, shops, prices)

#### Multi-tenant handling
- App login asks for tenant code (e.g. "zergo001")
- App stores tenant code and sends it in every API request header
- Django middleware reads the header and switches to correct schema

#### Offline sync flow
1. App downloads master data when online: products, shops, prices, routes
2. Rep goes offline → works normally, all actions saved locally
3. When back online: app uploads the offline queue (bills, returns, etc.)
4. Server processes each item, returns success/failure per item
5. App updates local records with server-assigned IDs

### Document number conflict prevention
See `USER_SPECIFIC_NUMBERING_PLAN.md`
- Each user generates numbers with their own namespace (SR01, DB01, AD01)
- Format: `BILL-001-SR01-20260715-0001`
- Zero conflicts when multiple users sync offline work

### Sync conflict resolution
- Server is always the source of truth for existing data
- Offline-created documents (new bills) are always new inserts — no update conflicts
- If same shop was edited offline and online: last-write-wins or flag for review

### What the app covers (same as web rep features)
- View assigned shops and route
- Create bills (add items, apply discounts)
- Record cash/cheque collections at shops
- Process returns and exchanges
- Print receipts via Bluetooth (Gooiprint PT-210)
- View EOD summary

### What stays web-only (office features)
- Purchasing (PO, GRN)
- Stock adjustments
- Bad debt write-off
- Commission management
- EOD reports review (manager)
- User and shop management
- Dashboard and reports

---

## iOS Situation

| | Phase 1 (WebView) | Phase 2 (React Native) |
|---|---|---|
| Android | ✅ Works | ✅ Works |
| iOS | ❌ Bluetooth blocked | ✅ Works (native CoreBluetooth) |

Phase 2 React Native uses native iOS Bluetooth (CoreBluetooth) which works
fine. Apple only blocks Web Bluetooth in browsers — native apps can use BLE freely.

For iOS in Phase 1: reps would need to use the mobile web browser and manually
share/export receipts without printing. Not ideal — push to Phase 2 for iOS.

---

## Build Order

1. **Now (prerequisite):** Assign user-specific employee IDs to all users
   and implement user-specific document numbering (see `USER_SPECIFIC_NUMBERING_PLAN.md`)

2. **Phase 1 (short term):** Android WebView APK for Android reps
   - Bluetooth printing works
   - Requires internet (no offline)
   - Can be deployed within days

3. **Phase 2 (long term):** React Native app for full offline + iOS support
   - Requires building REST API on Django side
   - Requires React Native app development
   - Takes weeks to months

---

## Tech Stack Summary

| Component | Phase 1 | Phase 2 |
|---|---|---|
| Mobile framework | Android WebView (Kotlin/Capacitor) | React Native (Expo) |
| Backend | Existing Django (no change) | Existing Django + DRF REST API |
| Offline storage | None (online only) | SQLite on device |
| Bluetooth | Android WebView BLE bridge | react-native-ble-plx |
| Auth | Web session (cookie) | Token / JWT |
| iOS support | ❌ | ✅ |
| Offline support | ❌ | ✅ |
| Build time | Days | Weeks–months |
