# Timezone Checker - Testing Guide

## Important Note: VPN Won't Work for Testing

**VPN changes your IP address, but JavaScript's `Intl.DateTimeFormat().resolvedOptions().timeZone` detects your computer's SYSTEM timezone, not your IP-based location.**

This means:
- ✅ VPN changes your IP → Good for testing IP-based features
- ❌ VPN does NOT change JavaScript timezone detection → Won't trigger timezone mismatch

## How Timezone Detection Works

The timezone checker uses:
```javascript
Intl.DateTimeFormat().resolvedOptions().timeZone
```

This returns your **system's timezone setting**, not your IP location.

## How to Test the Timezone Checker

### Method 1: Test Button (Easiest - Recommended) ⭐

1. Look for the **globe icon** (🌐) in the navbar (next to the notification bell)
2. Click it to open the timezone test dropdown
3. Select a test timezone from the list (e.g., "Europe/London")
4. The page will reload and the popup should appear comparing your saved timezone with the test timezone
5. To reset, click the globe icon again and click "Reset to Actual"

**Available test timezones:**
- Europe/London
- America/New_York
- Asia/Tokyo
- Australia/Sydney
- Europe/Berlin
- America/Los_Angeles

### Method 2: Console Test Mode

1. Open your browser's Developer Console (F12)
2. Go to the Console tab
3. Before refreshing the page, run this command:
   ```javascript
   window.TEST_TIMEZONE = 'Europe/London';
   ```
4. Refresh the page (F5)
5. The popup should appear comparing your saved timezone (Europe/Prague) with the test timezone (Europe/London)

**To test different timezones:**
```javascript
window.TEST_TIMEZONE = 'America/New_York';  // Test US Eastern Time
window.TEST_TIMEZONE = 'Asia/Tokyo';        // Test Japan Time
window.TEST_TIMEZONE = 'Australia/Sydney'; // Test Australia Time
```

**Note:** The test button uses `sessionStorage`, so it persists across page reloads. Console method uses `window.TEST_TIMEZONE` which also works but is less persistent.

### Method 2: Change System Timezone (Most Realistic)

**On macOS:**
1. Go to System Settings → General → Date & Time
2. Click "Time Zone" 
3. Change to a different timezone (e.g., London)
4. Refresh your browser page
5. The popup should appear

**On Windows:**
1. Settings → Time & Language → Date & Time
2. Turn off "Set time zone automatically"
3. Select a different timezone
4. Refresh your browser page

**On Linux:**
```bash
sudo timedatectl set-timezone Europe/London
```

### Method 3: Manual Database Change (For Testing)

1. Go to Django Admin: `/admin/accounts/mentorprofile/`
2. Find your mentor profile
3. Change the `time_zone` field to something different (e.g., `Europe/London`)
4. Save
5. Refresh your dashboard page
6. The popup should appear comparing the saved timezone (London) with your detected timezone (Prague)

## How It Works

### On Registration
- **No timezone is set** during registration
- On **first login**, JavaScript auto-detects and saves the timezone silently
- No popup is shown on first detection

### On Subsequent Visits
- If saved timezone **matches** detected timezone → No popup
- If saved timezone **differs** from detected timezone → Popup appears

### Popup Behavior
- Shows both timezones side-by-side
- Shows current time in both timezones
- "Keep Current" → Closes popup, keeps saved timezone
- "Update Timezone" → Updates saved timezone to detected one

## Testing Checklist

- [ ] First-time user (no timezone saved) → Auto-detects and saves silently
- [ ] User with matching timezone → No popup
- [ ] User with different timezone → Popup appears
- [ ] "Keep Current" button → Closes popup, no change
- [ ] "Update Timezone" button → Updates and reloads page
- [ ] After update → No popup on next visit (timezones match)

## Debug Console Logs

When testing, check the browser console for these logs:
```
[Timezone Checker] Initializing...
[Timezone Checker] Saved timezone: Europe/Prague
[Timezone Checker] Detected timezone: Europe/London
[Timezone Checker] ⚠️ MISMATCH DETECTED! Showing modal...
```

If you see "Timezones match", the popup won't appear (which is correct behavior).

## Check Current Timezone Status

**In the browser console, type:**
```javascript
checkTimezone()
```

This will show you:
- 📌 Your saved timezone
- 🔍 Your detected timezone  
- 🧪 Any test timezone currently set
- 💾 sessionStorage status
- 🪟 window.TEST_TIMEZONE status

**You can also click the globe icon (🌐) in the navbar** - it will automatically log the timezone status to the console each time you click it.

