# Weather API Dashboard

A FastAPI-based weather dashboard that provides current weather, hourly forecasts, and daily forecasts with a beautiful web interface.

## Features

- 🌤️ Current weather conditions
- ⏰ 24-hour hourly forecast
- 📅 7-day daily forecast
- 🌍 Location-based weather using geolocation
- 🔍 City search functionality
- 💨 Air quality index (AQI)
- 📱 Responsive web interface
- 🎨 Dynamic backgrounds based on weather conditions

## Quick Start

1. **Install Dependencies**
   ```bash
   # Create and activate virtual environment (recommended)
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install required packages
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access the Dashboard**
   - Open your browser to `http://localhost:8000`
   - Allow geolocation permission when prompted
   - Or use the search bar to find weather for any city

## API Endpoints

- `GET /weather?lat={lat}&lon={lon}` - Current weather
- `GET /hourly?lat={lat}&lon={lon}` - 24-hour forecast
- `GET /forecast?lat={lat}&lon={lon}` - 7-day forecast
- `GET /aqi-alerts?lat={lat}&lon={lon}` - Air quality and alerts
- `GET /docs` - Interactive API documentation (Swagger UI)

## Database

The app uses PostgreSQL (Supabase) for caching weather data. The connection string is configured in `app.py`. 

If you encounter database connection issues:
- The app will still work by fetching live data from Open-Meteo APIs
- Database is used only for caching to reduce API calls
- You can modify `DB_CONNECTION_STRING` in `app.py` to point to your own database

## Authentication

The project includes JWT-based authentication setup in `auth.py`, though it's not currently integrated into the main weather endpoints.

## Technologies Used

- **Backend**: FastAPI, Uvicorn
- **Database**: PostgreSQL (via psycopg2)
- **APIs**: Open-Meteo Weather API, Open-Meteo Geocoding API
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Authentication**: JWT tokens, bcrypt password hashing

## Troubleshooting

### "Failed to load data" in browser
- Check that the server is running on port 8000
- Ensure your browser allows geolocation
- Check browser console for specific error messages

### Database connection errors
- The app will fallback to live API data if database is unavailable
- Check that `DB_CONNECTION_STRING` is valid if you want caching

### Missing dependencies
- Run `pip install -r requirements.txt` to install all required packages
- Use a virtual environment to avoid conflicts

## Development

To run in development mode with auto-reload:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag automatically restarts the server when code changes are detected.