# Intro Gateway Control - Quick Guide

## Overview

The "AI Operations Gateway" is the futuristic black boot animation screen that appears before the login page. It shows system initialization phases with a 3-second animation sequence.

**Status**: ✅ Disabled by default (login page shows directly)

---

## How to Enable/Disable

### Option 1: Admin Panel (Recommended)

1. **Go to Admin Panel**: http://localhost:3005/admin
2. **Navigate to Config Tab**: Click "Configuration" in the sidebar
3. **Find "Login Gateway Animation"** section
4. **Toggle the button**:
   - 🟢 **Enable** - Shows 3-second boot animation before login
   - 🔴 **Disable** - Shows login form immediately

Changes take effect immediately on next login.

---

### Option 2: Direct Browser Console (Dev)

Open browser DevTools (F12) and run:

```javascript
// Enable intro gateway
localStorage.setItem('agentic_intro_gate_enabled', 'true');

// Disable intro gateway
localStorage.removeItem('agentic_intro_gate_enabled');

// Check current status
console.log(localStorage.getItem('agentic_intro_gate_enabled'));
```

---

## Technical Details

### File: `/services/ui-login/src/App.jsx`

The intro gateway is controlled by:

```javascript
const gateEnabled = localStorage.getItem('agentic_intro_gate_enabled');
if (gateEnabled !== 'true') {
  return false; // Gate disabled by default
}
```

### Admin Panel Integration

File: `/services/ui-console/views/admin.ejs`

- **UI Control Card**: Added to "Configuration" → "System Config" section
- **Functions**:
  - `loadIntroGatewayStatus()` - Loads current status from localStorage
  - `toggleIntroGateway(enable)` - Enables/disables the gateway

---

## What the Intro Gateway Shows

When **enabled**, users see:

1. **Black screen** with neural network animation
2. **Boot sequence phases**:
   - ✓ SCANNING ENVIRONMENT
   - ✓ INITIALIZING AGENTS
   - ✓ LOADING AUTH MODULES
   - ✓ CONNECTING DATA LAYER
   - ✓ VERIFYING INTEGRITY
   - ✓ AGENTIC PLATFORM ONLINE
3. **Progress bar** showing system initialization (0-100%)
4. **Futuristic animations** with neon accents
5. **Total duration**: ~3.2 seconds
6. **Then**: Login form appears

---

## Default Behavior

| Scenario | What Happens |
|----------|--------------|
| **First visit** | Login page shown directly (gateway disabled) |
| **After logout** | Login page shown directly (gateway skipped) |
| **With gateway enabled** | Boot animation plays, then login form |

---

## FAQ

**Q: Why is the gateway disabled by default?**
A: To provide the fastest login experience. Users who want the futuristic experience can enable it in Admin → Configuration.

**Q: Does it affect security?**
A: No. The gateway is purely cosmetic and doesn't affect authentication or security.

**Q: Can I customize the animation?**
A: Yes, edit `/services/ui-login/src/App.jsx` - the `PHASES` array and animation timings are easily customizable.

**Q: Does it work after logout?**
A: No, the gateway is skipped after logout to ensure fast re-authentication.

---

## Version Info

- **Added**: September 10, 2026
- **Default State**: Disabled ✅
- **Configurable**: Via Admin Panel or localStorage
- **Files Modified**:
  - `/services/ui-console/views/admin.ejs` - Added control UI + functions
  - `/services/ui-login/src/App.jsx` - Already had toggleable logic

---

## Quick Links

- **Admin Panel**: http://localhost:3005/admin
- **Config Section**: http://localhost:3005/admin#config
- **Login Page**: http://localhost:3005/login-app/

---

**Need help?** The toggle is easy to use and can be enabled/disabled anytime from the admin panel without restarting any services!
