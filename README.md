# 🌦️ IntelliWeather

A modern, feature-rich weather dashboard built with FastAPI and a responsive glassmorphism UI. Get real-time weather data, hourly forecasts, 7-day predictions, and air quality information for any location worldwide.

![Dashboard](https://github.com/user-attachments/assets/5a3e9289-f19e-4858-9eee-a82a04c9c0ad)

## ✨ Features

- **Real-time Weather Data** - Current temperature, humidity, wind speed, UV index, and more
- **Hourly Forecasts** - 24-hour detailed weather predictions
- **7-Day Forecast** - Extended weather outlook with high/low temperatures
- **Air Quality Index** - AQI monitoring with health indicators
- **Location Search** - Search for any city worldwide
- **Geolocation Support** - Automatic location detection
- **Dynamic Themes** - Background changes based on weather conditions (sunny, cloudy, rainy, snowy)
- **Responsive Design** - Works seamlessly on mobile, tablet, and desktop
- **Connection Status** - Real-time indicator showing backend connectivity

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Database for caching weather data
- **Supabase** - Cloud database hosting
- **Open-Meteo API** - Weather data provider

### Frontend
- **HTML5/CSS3** - Glassmorphism design with backdrop blur
- **Vanilla JavaScript** - No framework dependencies
- **Inter Font** - Modern typography

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database (or Supabase account)
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/CodersAcademy006/Weather-API.git
   cd Weather-API
   ```

2. **Install dependencies**
   ```bash
   pip install fastapi uvicorn requests psycopg2-binary python-jose passlib bcrypt
   ```

3. **Configure the database**
   
   Update the `DB_CONNECTION_STRING` in `app.py` with your PostgreSQL connection string.

4. **Run the server**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

5. **Open in browser**
   
   Navigate to `http://localhost:8000` to view the dashboard.

## 📡 API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/weather` | GET | Current weather data | `lat`, `lon` |
| `/hourly` | GET | 24-hour forecast | `lat`, `lon` |
| `/forecast` | GET | 7-day forecast | `lat`, `lon` |
| `/aqi-alerts` | GET | Air quality & alerts | `lat`, `lon` |

### Example Request

```bash
curl "http://localhost:8000/weather?lat=40.7128&lon=-74.0060"
```

### Example Response

```json
{
  "source": "live",
  "temperature_c": 22.5,
  "humidity_pct": 65,
  "wind_speed_mps": 3.5,
  "weather_code": 2,
  "apparent_temperature": 23.1,
  "uv_index": 5.2,
  "is_day": 1
}
```

## 🎨 Screenshots

| Login | Sign Up |
|-------|---------|
| ![Login](https://github.com/user-attachments/assets/d89050fb-aa97-4dcc-ab96-a1883e3b7aac) | ![Sign Up](https://github.com/user-attachments/assets/82d424be-c220-4c11-80cb-fa42eeb34fd6) |

## 🏗️ Architecture

```
Weather-API/
├── app.py              # FastAPI backend with API endpoints
├── auth.py             # Authentication utilities (JWT, OAuth)
├── static/
│   ├── index.html      # Main weather dashboard
│   ├── login.html      # Login page
│   ├── signup.html     # Registration page
│   └── google-callback.html  # OAuth callback handler
├── .gitignore          # Git ignore rules
├── LICENSE             # MIT License
└── README.md           # This file
```

## 🔧 System Design Features

- **Caching Layer** - Weather data cached in PostgreSQL to reduce API calls
- **Retry Logic** - Automatic retries with exponential backoff (3 attempts)
- **Request Timeouts** - 10-second timeout on all API requests
- **Connection Status** - Real-time indicator showing Connected/Connecting/Disconnected
- **Error Handling** - Graceful error display with retry functionality
- **Privacy** - GPS coordinates rounded to 2 decimal places (~1km precision)

## 🌐 Data Sources

- **Weather Data**: [Open-Meteo](https://open-meteo.com/) - Free weather API
- **Air Quality**: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- **Geocoding**: [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

Created by [@CodersAcademy006](https://github.com/CodersAcademy006)

---

⭐ Star this repo if you find it helpful!
