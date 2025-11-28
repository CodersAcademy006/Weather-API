"""
Admin Dashboard Routes

Provides protected admin analytics and dashboard endpoints.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from config import settings
from logging_config import get_logger
from cache import get_cache
from storage import get_storage
from metrics import get_metrics
from session_middleware import require_auth

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin access required"}
    }
)


class DashboardStats(BaseModel):
    """Dashboard statistics model."""
    total_users: int = Field(..., description="Total registered users")
    active_sessions: int = Field(..., description="Currently active sessions")
    logins_24h: int = Field(..., description="Logins in the last 24 hours")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    cache_hits: int = Field(..., description="Total cache hits")
    cache_misses: int = Field(..., description="Total cache misses")
    cache_size: int = Field(..., description="Current cache size")
    top_locations: List[Dict[str, Any]] = Field(..., description="Top searched locations")
    alerts_count: int = Field(..., description="Active alerts count")
    last_refresh: str = Field(..., description="Last data refresh timestamp")
    system_uptime: str = Field(..., description="System uptime")
    recent_errors: List[str] = Field(..., description="Recent error messages")


class SystemHealth(BaseModel):
    """System health status."""
    status: str
    storage_writable: bool
    cache_operational: bool
    sessions_operational: bool
    api_reachable: bool
    timestamp: str


def check_admin(user) -> bool:
    """Check if user has admin privileges."""
    # Check if user email is in admin list
    if settings.is_admin(user.email):
        return True
    # Also allow if username starts with 'admin'
    if user.username.lower().startswith("admin"):
        return True
    return False


async def require_admin(user = Depends(require_auth)):
    """Dependency to require admin access."""
    if not check_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return user


@router.get(
    "/api/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Get aggregated statistics for the admin dashboard."
)
async def get_dashboard_stats(
    request: Request,
    user = Depends(require_admin)
):
    """Get dashboard statistics."""
    storage = get_storage()
    cache = get_cache()
    metrics = get_metrics()
    
    # Get storage stats
    storage_stats = storage.get_stats()
    
    # Get cache stats
    cache_stats = cache.stats()
    
    # Get metrics
    metrics_data = metrics.get_all()
    
    # Calculate cache hit rate
    total_cache_requests = cache_stats["hits"] + cache_stats["misses"]
    hit_rate = (cache_stats["hits"] / total_cache_requests * 100) if total_cache_requests > 0 else 0
    
    # Get top searched locations (mock data for now)
    top_locations = [
        {"name": "New York", "lat": 40.71, "lon": -74.01, "searches": 150},
        {"name": "London", "lat": 51.51, "lon": -0.13, "searches": 120},
        {"name": "Tokyo", "lat": 35.68, "lon": 139.65, "searches": 95},
        {"name": "Paris", "lat": 48.86, "lon": 2.35, "searches": 80},
        {"name": "Mumbai", "lat": 19.08, "lon": 72.88, "searches": 75}
    ]
    
    return DashboardStats(
        total_users=storage_stats["users_count"],
        active_sessions=storage_stats["sessions_count"],
        logins_24h=metrics_data.get("logins_24h", 0),
        cache_hit_rate=round(hit_rate, 2),
        cache_hits=cache_stats["hits"],
        cache_misses=cache_stats["misses"],
        cache_size=cache_stats["size"],
        top_locations=top_locations,
        alerts_count=metrics_data.get("active_alerts", 0),
        last_refresh=datetime.now(timezone.utc).isoformat(),
        system_uptime=metrics_data.get("uptime", "Unknown"),
        recent_errors=[]
    )


@router.get(
    "/api/health",
    response_model=SystemHealth,
    summary="Get system health status",
    description="Check the health of all system components."
)
async def get_system_health(
    request: Request,
    user = Depends(require_admin)
):
    """Get detailed system health status."""
    storage = get_storage()
    cache = get_cache()
    
    # Check storage
    storage_ok = storage.is_writable()
    
    # Check cache
    try:
        cache.set("health_check", "ok", ttl=10)
        cache_ok = cache.get("health_check") == "ok"
    except Exception:
        cache_ok = False
    
    # Check API connectivity
    api_ok = True
    try:
        import requests
        response = requests.get(
            f"{settings.OPEN_METEO_API_URL}?latitude=0&longitude=0&current=temperature_2m",
            timeout=5
        )
        api_ok = response.status_code == 200
    except Exception:
        api_ok = False
    
    overall_status = "healthy" if all([storage_ok, cache_ok, api_ok]) else "degraded"
    
    return SystemHealth(
        status=overall_status,
        storage_writable=storage_ok,
        cache_operational=cache_ok,
        sessions_operational=True,
        api_reachable=api_ok,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get(
    "/api/metrics",
    summary="Get detailed metrics",
    description="Get detailed application metrics."
)
async def get_detailed_metrics(
    request: Request,
    user = Depends(require_admin)
):
    """Get detailed application metrics."""
    metrics = get_metrics()
    cache = get_cache()
    storage = get_storage()
    
    return {
        "counters": metrics.get_all(),
        "cache": cache.stats(),
        "storage": storage.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post(
    "/api/cache/clear",
    summary="Clear application cache",
    description="Clear all cached data. Use with caution."
)
async def clear_cache(
    request: Request,
    user = Depends(require_admin)
):
    """Clear the application cache."""
    cache = get_cache()
    cache.clear()
    
    logger.warning(f"Cache cleared by admin: {user.username}")
    
    return {
        "message": "Cache cleared successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Admin dashboard page",
    description="Render the admin dashboard HTML page."
)
async def admin_dashboard(
    request: Request,
    user = Depends(require_admin)
):
    """Render the admin dashboard."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IntelliWeather Admin Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                min-height: 100vh;
                color: #fff;
            }
            .header {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 1.5rem; color: #d4af37; }
            .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            .stat-card {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 12px;
                padding: 1.5rem;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .stat-card h3 { color: #888; font-size: 0.9rem; margin-bottom: 0.5rem; }
            .stat-card .value { font-size: 2rem; font-weight: bold; color: #d4af37; }
            .section { margin-bottom: 2rem; }
            .section h2 { margin-bottom: 1rem; color: #d4af37; }
            .table {
                width: 100%;
                background: rgba(255,255,255,0.1);
                border-radius: 12px;
                overflow: hidden;
            }
            .table th, .table td { padding: 1rem; text-align: left; }
            .table th { background: rgba(0,0,0,0.3); }
            .table tr:hover { background: rgba(255,255,255,0.05); }
            .health-badge {
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.8rem;
            }
            .health-badge.healthy { background: #10b981; }
            .health-badge.degraded { background: #f59e0b; }
            .btn {
                background: #d4af37;
                color: #000;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
            }
            .btn:hover { background: #b8960c; }
            #loading { text-align: center; padding: 2rem; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>👑 IntelliWeather Admin</h1>
            <span id="user-info">Loading...</span>
        </div>
        
        <div class="container">
            <div id="loading">Loading dashboard data...</div>
            
            <div id="dashboard" style="display: none;">
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Users</h3>
                        <div class="value" id="total-users">-</div>
                    </div>
                    <div class="stat-card">
                        <h3>Active Sessions</h3>
                        <div class="value" id="active-sessions">-</div>
                    </div>
                    <div class="stat-card">
                        <h3>Cache Hit Rate</h3>
                        <div class="value" id="cache-hit-rate">-</div>
                    </div>
                    <div class="stat-card">
                        <h3>Cache Size</h3>
                        <div class="value" id="cache-size">-</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>System Health</h2>
                    <div id="health-status">Loading...</div>
                </div>
                
                <div class="section">
                    <h2>Top Searched Locations</h2>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Location</th>
                                <th>Coordinates</th>
                                <th>Searches</th>
                            </tr>
                        </thead>
                        <tbody id="top-locations">
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>Actions</h2>
                    <button class="btn" onclick="clearCache()">Clear Cache</button>
                    <button class="btn" onclick="refreshData()">Refresh Data</button>
                </div>
            </div>
        </div>
        
        <script>
            async function loadDashboard() {
                try {
                    const [statsRes, healthRes] = await Promise.all([
                        fetch('/admin/api/stats'),
                        fetch('/admin/api/health')
                    ]);
                    
                    if (!statsRes.ok || !healthRes.ok) {
                        throw new Error('Failed to load data');
                    }
                    
                    const stats = await statsRes.json();
                    const health = await healthRes.json();
                    
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('dashboard').style.display = 'block';
                    
                    document.getElementById('total-users').textContent = stats.total_users;
                    document.getElementById('active-sessions').textContent = stats.active_sessions;
                    document.getElementById('cache-hit-rate').textContent = stats.cache_hit_rate + '%';
                    document.getElementById('cache-size').textContent = stats.cache_size;
                    
                    const healthHtml = `
                        <span class="health-badge ${health.status}">${health.status.toUpperCase()}</span>
                        <ul style="margin-top: 1rem; margin-left: 1rem;">
                            <li>Storage: ${health.storage_writable ? '✅' : '❌'}</li>
                            <li>Cache: ${health.cache_operational ? '✅' : '❌'}</li>
                            <li>API: ${health.api_reachable ? '✅' : '❌'}</li>
                        </ul>
                    `;
                    document.getElementById('health-status').innerHTML = healthHtml;
                    
                    const locationsHtml = stats.top_locations.map(loc => `
                        <tr>
                            <td>${loc.name}</td>
                            <td>${loc.lat}, ${loc.lon}</td>
                            <td>${loc.searches}</td>
                        </tr>
                    `).join('');
                    document.getElementById('top-locations').innerHTML = locationsHtml;
                    
                } catch (error) {
                    document.getElementById('loading').textContent = 'Error loading dashboard: ' + error.message;
                }
            }
            
            async function clearCache() {
                if (!confirm('Are you sure you want to clear the cache?')) return;
                try {
                    const res = await fetch('/admin/api/cache/clear', { method: 'POST' });
                    if (res.ok) {
                        alert('Cache cleared successfully');
                        refreshData();
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            function refreshData() {
                loadDashboard();
            }
            
            loadDashboard();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
