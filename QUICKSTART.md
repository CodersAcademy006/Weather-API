# Weather API Dashboard - Quick Start Guide

## 🚨 CRITICAL: How to Access the Dashboard

The server is running on **PORT 8000**. You MUST access it correctly:

### ✅ CORRECT Way (Codespaces):
1. Look at the bottom panel in VS Code
2. Click the **"PORTS"** tab (next to Terminal)
3. Find port **8000** in the list
4. Click the **🌐 Globe icon** next to port 8000
5. A new browser tab will open with the correct URL

### ❌ WRONG Ways:
- ❌ Do NOT use "Open with Live Server" (uses port 5500)
- ❌ Do NOT open index.html directly from file explorer
- ❌ Do NOT use any port other than 8000

## 🏃 Running the Server

### Option 1: Using restart script (RECOMMENDED)
```bash
python3 restart.py
```

### Option 2: Manual
```bash
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 Testing if API Works

### Test Page
Open: `http://localhost:8000/test.html`
(or your Codespaces forwarded URL + `/test.html`)

### Quick API Check
```bash
curl http://localhost:8000/api-test
```

Should return:
```json
{"status":"ok","message":"Weather API is running!","timestamp":"..."}
```

## 🐛 Troubleshooting "404" Error

If you see **"Weather API failed: 404"**:

1. ✅ Server running? Check with: `ps aux | grep uvicorn`
2. ✅ Correct port? Must be **8000**, not 5500 or others
3. ✅ Using forwarded URL? Check PORTS tab in VS Code
4. ✅ API responding? Visit `/test.html` page

## 📁 Project Structure

```
Weather-API/
├── app.py              # Main FastAPI backend
├── restart.py          # Helper to restart server
├── start_server.py     # Alternative start script
├── requirements.txt    # Python dependencies
├── weather.db          # Local SQLite database (auto-created)
└── static/
    ├── index.html      # Main dashboard
    ├── test.html       # API test page
    └── ...
```

## 🔧 Features

- ☀️ Current weather with live location
- ⏰ 24-hour hourly forecast
- 📅 7-day daily forecast  
- 💨 Air quality index
- 🗄️ Local SQLite caching
- 🔄 Auto-refresh every 15 minutes

## 📞 Still Not Working?

1. Stop the server: Press `Ctrl+C` in terminal
2. Restart: `python3 restart.py`
3. Open test page: `http://localhost:8000/test.html`
4. Check browser console for errors (F12 → Console tab)
