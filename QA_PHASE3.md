# Phase 3 QA Checklist

This document provides a comprehensive QA checklist for verifying all Phase 3 features.

## Prerequisites

- Docker installed
- Node.js 18+ (for local development)
- kubectl (for Kubernetes testing)
- kind or minikube (for local k8s)

## 1. Professional UI & Animations

### Header
- [ ] Logo displays correctly with icon and text
- [ ] Navigation links are visible (Dashboard, Maps, Alerts, Historical, API Docs)
- [ ] Theme toggle button works
- [ ] Sign In / Get Started buttons visible
- [ ] Header has blur backdrop effect
- [ ] Header shadow appears on scroll

### Footer
- [ ] Logo in footer brand section
- [ ] Social links display (Twitter, Facebook, Instagram, GitHub)
- [ ] Product links column visible
- [ ] Resources links column visible
- [ ] Company links column visible
- [ ] Copyright text with Open-Meteo attribution
- [ ] Language selector present

### Dark/Light Mode
```bash
# Test in browser console
localStorage.setItem('intelliweather-theme', 'dark');
location.reload();

localStorage.setItem('intelliweather-theme', 'light');
location.reload();
```
- [ ] Light mode: light background, dark text
- [ ] Dark mode: dark background, light text
- [ ] Theme persists across page reloads
- [ ] Transition is smooth (no flash)

### Animations
- [ ] Page entrance animation (fade in + slide up)
- [ ] Weather icon bounces smoothly
- [ ] Shimmer effect on weather card
- [ ] Hourly items animate in with stagger
- [ ] Daily items animate in with stagger
- [ ] Hover effects on cards (lift + shadow)
- [ ] Tab transitions are smooth

### Reduced Motion
```bash
# Test with system preference
# macOS: System Preferences > Accessibility > Display > Reduce motion
# Windows: Settings > Ease of Access > Display > Show animations
```
- [ ] Animations disabled when reduced motion enabled
- [ ] App still functions correctly

### Responsive Design
- [ ] Desktop (1200px+): Full header nav visible
- [ ] Tablet (768-1024px): Adjusted layout
- [ ] Mobile (< 768px): Mobile menu toggle, stacked layout

## 2. Kubernetes Deployment

### Prerequisites
```bash
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

### Local Setup
```bash
cd k8s/local
chmod +x local-setup.sh

# Full setup
./local-setup.sh setup

# Check status
./local-setup.sh status

# Port forward
./local-setup.sh forward
```

- [ ] kind cluster creates successfully
- [ ] Docker image builds
- [ ] Image loads into kind
- [ ] Pods start (Running state)
- [ ] Service is accessible via port-forward
- [ ] Health endpoint responds: `curl http://localhost:8080/healthz`

### Manifest Verification
```bash
# Validate manifests
kubectl apply -f k8s/deployment.yaml --dry-run=client

# Check resources created
kubectl get all -n intelliweather
```
- [ ] Deployment creates with 3 replicas
- [ ] Service exposes port 80
- [ ] Ingress configured (nginx class)
- [ ] HPA configured (2-10 replicas)
- [ ] PVC claims storage
- [ ] PDB ensures availability

### Cleanup
```bash
./local-setup.sh cleanup
```
- [ ] Cluster deleted successfully

## 3. Helm Chart

```bash
cd helm/intelliweather

# Lint chart
helm lint .

# Template rendering
helm template intelliweather . --debug

# Install (if kind cluster running)
helm install intelliweather . --namespace intelliweather --create-namespace --dry-run
```

- [ ] Chart.yaml has correct version
- [ ] values.yaml has all required fields
- [ ] Template renders without errors
- [ ] Dependencies declared (redis, postgresql optional)

## 4. Monitoring & Observability

### Prometheus Metrics
```bash
# Start application
docker-compose up -d

# Check metrics endpoint
curl http://localhost:8000/metrics/prometheus
```

- [ ] `http_request_total` counter exists
- [ ] `http_request_duration_seconds` histogram exists
- [ ] `cache_hits_total` counter exists
- [ ] `cache_misses_total` counter exists
- [ ] `active_sessions` gauge exists

### Prometheus Config
- [ ] `monitoring/prometheus.yml` valid YAML
- [ ] Scrape configs defined for intelliweather
- [ ] Kubernetes SD config present

### Grafana Dashboard
```bash
# Import dashboard
# 1. Open Grafana UI
# 2. Go to Dashboards > Import
# 3. Upload monitoring/grafana-dashboard.json
```

- [ ] Dashboard JSON is valid
- [ ] Panels load without errors
- [ ] Request rate panel shows data
- [ ] Latency panel shows data
- [ ] Cache ratio gauge works

### Alert Rules
```bash
# Validate alert rules
promtool check rules monitoring/alert_rules.yml
```

- [ ] `HighErrorRate` alert defined
- [ ] `HighLatency` alert defined
- [ ] `LowCacheHitRatio` alert defined
- [ ] `ServiceDown` alert defined

## 5. Notifications Module

### Email (Mock)
```python
# Test in Python shell
from notifications import get_notification_service, NotificationType

service = get_notification_service()
result = await service.send(
    NotificationType.EMAIL,
    "test@example.com",
    "Test Subject",
    "Test body"
)
print(result.status)  # Should be 'sent' or 'failed'
```

- [ ] EmailBackend initializes
- [ ] Mock send logs message
- [ ] Real send works with SMTP configured
- [ ] SendGrid send works with API key

### SMS (Mock)
```python
result = await service.send(
    NotificationType.SMS,
    "+1234567890",
    "Test Alert",
    "Weather alert test"
)
```

- [ ] SMSBackend initializes
- [ ] Mock send logs message
- [ ] Twilio send works with credentials

### In-App
```python
result = await service.send(
    NotificationType.IN_APP,
    "user123",
    "Notification Title",
    "Notification body"
)

# Get notifications
notifications = service.get_user_notifications("user123")
print(len(notifications))
```

- [ ] InAppBackend always available
- [ ] Notifications stored in memory
- [ ] Get user notifications returns list
- [ ] Mark as read works

## 6. CI/CD Pipeline

### GitHub Actions
- [ ] `.github/workflows/ci-cd.yml` exists
- [ ] Test job runs pytest
- [ ] Build job builds Docker image
- [ ] Security scan job exists
- [ ] Deploy jobs conditional on branch/tag

### Local Validation
```bash
# Test workflow syntax
# Use act (https://github.com/nektos/act)
act -n  # Dry run

# Or validate YAML
yamllint .github/workflows/ci-cd.yml
```

## 7. Documentation

### DEPLOYMENT.md
- [ ] File exists at `docs/DEPLOYMENT.md`
- [ ] Docker quick start documented
- [ ] Kubernetes deployment documented
- [ ] Cloud provider examples (AWS, GCP, Azure)
- [ ] Environment variables table
- [ ] Health checks documented
- [ ] Scaling documented
- [ ] Troubleshooting section

### CDN.md
- [ ] File exists at `docs/CDN.md`
- [ ] Cloudflare setup documented
- [ ] Fastly setup documented
- [ ] Cache headers explained
- [ ] Edge worker example included
- [ ] Best practices section

## 8. Integration Tests

### Full Flow
```bash
# Start application
docker-compose up -d

# Run integration tests
pytest tests/ -v -m integration
```

### Manual Integration Test
```bash
# 1. Open browser to http://localhost:8000
# 2. Wait for location detection
# 3. Search for "London"
# 4. Select result
# 5. Verify weather updates
# 6. Switch to Hourly tab
# 7. Switch to 7-Day tab
# 8. Toggle dark mode
# 9. Check footer links
```

- [ ] Location detection works
- [ ] Search returns results
- [ ] Weather data displays
- [ ] Tabs switch correctly
- [ ] Theme toggle works
- [ ] Footer displays

## Summary

| Feature | Status |
|---------|--------|
| Professional UI | ⬜ |
| Dark/Light Mode | ⬜ |
| Animations | ⬜ |
| Kubernetes | ⬜ |
| Helm Chart | ⬜ |
| Prometheus | ⬜ |
| Grafana Dashboard | ⬜ |
| Alert Rules | ⬜ |
| Notifications | ⬜ |
| CI/CD | ⬜ |
| Documentation | ⬜ |

Legend: ✅ Pass | ❌ Fail | ⬜ Not Tested
