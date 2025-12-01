#!/bin/bash
# Comprehensive IntelliWeather API Test Suite

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║        📡 INTELLIWEATHER - COMPREHENSIVE API TEST SUITE            ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    echo -n "  Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" = "$expected_status" ]; then
        echo "✅ PASS (HTTP $response)"
        ((PASSED++))
    else
        echo "❌ FAIL (HTTP $response, expected $expected_status)"
        ((FAILED++))
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 CORE ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_endpoint "Landing Page" "$BASE_URL/"
test_endpoint "Dashboard" "$BASE_URL/static/dashboard.html"
test_endpoint "API Docs" "$BASE_URL/docs"
test_endpoint "Metrics" "$BASE_URL/metrics"
test_endpoint "Health Check" "$BASE_URL/healthz"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌤️  FORECAST V3 ENDPOINTS (LEVEL 1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_endpoint "Nowcast (NYC)" "$BASE_URL/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060"
test_endpoint "Hourly Forecast" "$BASE_URL/api/v3/forecast/hourly?latitude=40.7128&longitude=-74.0060&hours=24"
test_endpoint "Daily Forecast" "$BASE_URL/api/v3/forecast/daily?latitude=40.7128&longitude=-74.0060&days=7"
test_endpoint "Complete Forecast" "$BASE_URL/api/v3/forecast/complete?latitude=40.7128&longitude=-74.0060"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗺️  GEOCODING ENDPOINTS (LEVEL 1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_endpoint "Search Location" "$BASE_URL/geocode/search?q=London"
test_endpoint "Autocomplete" "$BASE_URL/geocode/autocomplete?q=New"
test_endpoint "Popular Cities" "$BASE_URL/geocode/popular"
test_endpoint "Nearby Places" "$BASE_URL/geocode/nearby?latitude=40.7128&longitude=-74.0060&radius=50"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 INSIGHTS ENGINE (LEVEL 1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_endpoint "Current Insights" "$BASE_URL/api/v3/insights/current?latitude=40.7128&longitude=-74.0060"
test_endpoint "Fire Risk" "$BASE_URL/api/v3/insights/fire-risk?latitude=40.7128&longitude=-74.0060"
test_endpoint "UV Exposure" "$BASE_URL/api/v3/insights/uv-exposure?latitude=40.7128&longitude=-74.0060"
test_endpoint "Event Safety" "$BASE_URL/api/v3/insights/event-safety?latitude=40.7128&longitude=-74.0060"
test_endpoint "Allergy Forecast" "$BASE_URL/api/v3/insights/allergy-forecast?latitude=40.7128&longitude=-74.0060"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌸 LEVEL 2 FEATURES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_endpoint "Pollen Data" "$BASE_URL/api/v2/pollen/current?latitude=40.7128&longitude=-74.0060"
test_endpoint "Solar Data" "$BASE_URL/api/v2/solar/current?latitude=40.7128&longitude=-74.0060"
test_endpoint "Air Quality (AQI V2)" "$BASE_URL/api/v2/air-quality/current?latitude=40.7128&longitude=-74.0060"
test_endpoint "Marine Conditions" "$BASE_URL/api/v2/marine/current?latitude=40.7128&longitude=-74.0060"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔔 ALERTS SYSTEM (LEVEL 1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_endpoint "Get Alerts" "$BASE_URL/api/alerts?latitude=40.7128&longitude=-74.0060"
test_endpoint "Get Active Alerts" "$BASE_URL/api/alerts/active?latitude=40.7128&longitude=-74.0060"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ✅ PASSED: $PASSED"
echo "  ❌ FAILED: $FAILED"
TOTAL=$((PASSED + FAILED))
SUCCESS_RATE=$((PASSED * 100 / TOTAL))
echo "  📈 Success Rate: $SUCCESS_RATE%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED! IntelliWeather is fully operational."
else
    echo "⚠️  Some tests failed. Check the API logs for details."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
