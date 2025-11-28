# Phase 3 Demo Script

This guide walks through demonstrating all Phase 3 features of IntelliWeather.

## Prerequisites

- Docker Desktop running
- Terminal/command line access
- Web browser (Chrome/Firefox recommended)

## Setup

```bash
# Clone and navigate to repository
cd Weather-API

# Start the application
docker-compose up -d --build

# Verify it's running
curl http://localhost:8000/healthz
```

## Demo Flow (15-20 minutes)

### 1. Professional UI Overview (3 min)

**Open Browser**: Navigate to `http://localhost:8000`

**Header Tour**:
- Point out the IntelliWeather logo with weather icon
- Show navigation links: Dashboard, Maps, Alerts, Historical, API Docs
- Highlight the theme toggle button (moon/sun icon)
- Show Sign In / Get Started buttons

**Dashboard**:
- Location automatically detected (or defaults to New York)
- Current date displayed
- Search box with magnifying glass icon
- Tab navigation: Now, Hourly, 7-Day

**Weather Display**:
- Large weather icon with bounce animation
- Temperature with gradient text effect
- Weather description
- Details grid: Feels Like, Humidity, Wind, UV Index, Air Quality, Precipitation

**Footer Tour**:
- Scroll to bottom of page
- Show branding with logo and description
- Point out social media links
- Product, Resources, Company link columns
- Copyright and language selector

### 2. Dark/Light Mode (2 min)

**Toggle Theme**:
```
Click the moon icon in the header
```

**Observe**:
- Smooth transition (no flash)
- Background changes from light to dark
- Text colors invert
- Cards adjust styling
- Footer updates

**Persistence**:
```
1. Refresh the page (F5)
2. Theme stays in dark mode
3. Click sun icon to switch back to light
```

**System Preference**:
- Mention that first visit respects system preference
- Demo by changing system dark mode setting (if time permits)

### 3. Animation System (2 min)

**Page Animations**:
- Refresh page to see entrance animation
- Dashboard fades in and slides up
- Weather card has shimmer effect

**Interaction Animations**:
```
1. Hover over a detail card
2. Card lifts up with shadow
3. Switch to Hourly tab
4. Items animate in with stagger effect
5. Hover over hourly item - rises and glows
6. Switch to 7-Day tab
7. Items slide in from left with stagger
```

**Weather Icon**:
- Point out the gentle bounce animation
- Mention it uses `requestAnimationFrame` for smoothness

**Reduced Motion**:
```
If demonstrating accessibility:
1. Open system preferences
2. Enable "Reduce motion"
3. Refresh page
4. Animations are disabled
```

### 4. Search Experience (2 min)

**Search Flow**:
```
1. Click in search box
2. Type "London"
3. See loading spinner
4. Results appear with animation
5. Use arrow keys to navigate
6. Press Enter or click to select
```

**Features to Highlight**:
- Debounced search (300ms delay)
- Keyboard navigation support
- Smooth dropdown animation
- Arrow indicator on hover/selection

### 5. Kubernetes Deployment (3 min)

**Show Manifests**:
```bash
# Open k8s/deployment.yaml in editor
cat k8s/deployment.yaml | head -50
```

**Highlight**:
- Deployment with 3 replicas
- Resource limits (100m CPU, 256Mi memory)
- Health probes (liveness, readiness)
- HorizontalPodAutoscaler (2-10 replicas)
- PodDisruptionBudget

**Local Demo** (if kind installed):
```bash
cd k8s/local
./local-setup.sh setup

# Check status
./local-setup.sh status

# Show pods
kubectl get pods -n intelliweather

# Port forward
./local-setup.sh forward
# Then open http://localhost:8080
```

**Helm Chart**:
```bash
# Show Helm structure
ls -la helm/intelliweather/

# View values
cat helm/intelliweather/values.yaml | head -30
```

### 6. Monitoring & Observability (3 min)

**Prometheus Metrics**:
```bash
# View metrics endpoint
curl http://localhost:8000/metrics/prometheus

# Key metrics:
# - http_request_total
# - http_request_duration_seconds
# - cache_hits_total
# - active_sessions
```

**Show Grafana Dashboard**:
```bash
# Open the JSON file
cat monitoring/grafana-dashboard.json | jq '.panels[].title'
```

**Panels include**:
- Request Rate by Method
- Response Latency (p50, p95, p99)
- Cache Hit Ratio gauge
- Active Sessions stat
- Requests by Status Code
- CPU/Memory gauges

**Alert Rules**:
```bash
cat monitoring/alert_rules.yml | grep "alert:"
```

**Alerts**:
- HighErrorRate (>5% 5xx errors)
- HighLatency (>2s p95)
- LowCacheHitRatio (<50%)
- ServiceDown

### 7. Notifications System (2 min)

**Show Code Structure**:
```bash
cat notifications/__init__.py | head -100
```

**Features**:
- Pluggable backend architecture
- EmailBackend (SMTP + SendGrid)
- SMSBackend (Twilio)
- WebPushBackend
- InAppBackend

**Configuration**:
```bash
grep -A5 "Notifications" config.py
```

**Environment Variables**:
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `SENDGRID_API_KEY`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

### 8. CI/CD Pipeline (2 min)

**Show Workflow**:
```bash
cat .github/workflows/ci-cd.yml
```

**Pipeline Stages**:
1. **Test**: Run pytest with coverage
2. **Build**: Build multi-platform Docker image
3. **Security**: Trivy vulnerability scan
4. **Deploy Staging**: On develop branch
5. **Deploy Production**: On version tags (v*)

**Triggers**:
- Push to main/develop
- Pull requests to main
- Version tags (v*)

### 9. Documentation (1 min)

**Show Docs**:
```bash
# Deployment guide
head -50 docs/DEPLOYMENT.md

# CDN guide
head -50 docs/CDN.md
```

**Topics Covered**:
- Docker quick start
- Kubernetes deployment
- Cloud providers (AWS, GCP, Azure, DigitalOcean)
- Cloudflare/Fastly CDN setup
- Cache configuration
- Edge workers

## Q&A

**Common Questions**:

1. **Q: How do I deploy to production?**
   A: Use the Helm chart with your values.yaml or apply k8s manifests directly.

2. **Q: How do I enable real notifications?**
   A: Set the SMTP or SendGrid environment variables for email, Twilio for SMS.

3. **Q: Does it scale automatically?**
   A: Yes, HPA scales from 2-10 replicas based on CPU/memory.

4. **Q: How is caching handled?**
   A: In-memory by default, Redis optional for distributed caching.

5. **Q: What about HTTPS?**
   A: The Ingress supports TLS with cert-manager annotations.

## Cleanup

```bash
# Stop Docker containers
docker-compose down

# Delete kind cluster (if created)
./k8s/local/local-setup.sh cleanup
```

## Summary

Phase 3 transforms IntelliWeather into a production-ready application with:

✅ **Professional UI** - Modern design with header, footer, branding
✅ **Dark/Light Mode** - User preference with persistence
✅ **Smooth Animations** - Hardware-accelerated, accessibility-aware
✅ **Kubernetes Ready** - Full manifests and Helm chart
✅ **Observability** - Prometheus, Grafana, Alertmanager
✅ **Notifications** - Email, SMS, Push, In-App
✅ **CI/CD** - GitHub Actions with multi-stage pipeline
✅ **Documentation** - Deployment, CDN, troubleshooting guides
