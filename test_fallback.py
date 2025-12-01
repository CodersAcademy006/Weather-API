#!/usr/bin/env python3
"""
Test script to verify the fallback system works correctly.
"""

import requests
from config import settings

def test_weatherapi_fallback():
    """Test that WeatherAPI.com fallback works."""
    print("=" * 60)
    print("Testing WeatherAPI.com Fallback System")
    print("=" * 60)
    
    # Test coordinates (New York)
    lat, lon = 40.7128, -74.0060
    
    print(f"\n1. Configuration Check:")
    print(f"   WEATHERAPI_KEY: {settings.WEATHERAPI_KEY[:20]}...")
    print(f"   WEATHERAPI_URL: {settings.WEATHERAPI_URL}")
    print(f"   ENABLE_FALLBACK: {settings.ENABLE_FALLBACK}")
    
    print(f"\n2. Testing Direct WeatherAPI.com Call:")
    print(f"   Location: NYC ({lat}, {lon})")
    
    try:
        params = {
            "key": settings.WEATHERAPI_KEY,
            "q": f"{lat},{lon}",
            "days": 3,
            "aqi": "yes"
        }
        
        response = requests.get(settings.WEATHERAPI_URL, params=params, timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            location = data.get("location", {})
            current = data.get("current", {})
            
            print(f"   ✓ SUCCESS!")
            print(f"   Location: {location.get('name')}, {location.get('region')}, {location.get('country')}")
            print(f"   Temperature: {current.get('temp_c')}°C")
            print(f"   Condition: {current.get('condition', {}).get('text')}")
            print(f"   Humidity: {current.get('humidity')}%")
            print(f"   Wind: {current.get('wind_kph')} km/h")
            
            # Show hourly forecast
            forecast = data.get("forecast", {}).get("forecastday", [])
            if forecast:
                print(f"\n   Hourly Data Points: {len(forecast[0].get('hour', []))}")
                print(f"   Daily Forecast Days: {len(forecast)}")
            
            return True
        else:
            print(f"   ✗ FAILED: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_weatherapi_fallback()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ Fallback system is configured correctly!")
        print("=" * 60)
        exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗ Fallback system test failed!")
        print("=" * 60)
        exit(1)
