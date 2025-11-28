#!/bin/bash
# IntelliWeather - Local Kubernetes Setup Script
# Uses kind (Kubernetes in Docker) for local development

set -e

CLUSTER_NAME="intelliweather"
NAMESPACE="intelliweather"

echo "🌤️  IntelliWeather Local Kubernetes Setup"
echo "==========================================="

# Check dependencies
check_deps() {
    echo "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v kind &> /dev/null; then
        echo "❌ kind is not installed. Installing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install kind
        else
            curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
            chmod +x ./kind
            sudo mv ./kind /usr/local/bin/kind
        fi
    fi
    
    if ! command -v kubectl &> /dev/null; then
        echo "❌ kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    echo "✅ All dependencies are installed"
}

# Create kind cluster
create_cluster() {
    echo ""
    echo "Creating kind cluster..."
    
    if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        echo "Cluster '${CLUSTER_NAME}' already exists"
    else
        kind create cluster --name ${CLUSTER_NAME} --config - <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
      - containerPort: 30000
        hostPort: 30000
        protocol: TCP
EOF
        echo "✅ Cluster created"
    fi
}

# Build and load Docker image
build_image() {
    echo ""
    echo "Building Docker image..."
    
    cd "$(dirname "$0")/.."
    docker build -t intelliweather:latest .
    
    echo "Loading image into kind cluster..."
    kind load docker-image intelliweather:latest --name ${CLUSTER_NAME}
    
    echo "✅ Image built and loaded"
}

# Install NGINX Ingress Controller
install_ingress() {
    echo ""
    echo "Installing NGINX Ingress Controller..."
    
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    
    echo "Waiting for ingress controller to be ready..."
    kubectl wait --namespace ingress-nginx \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/component=controller \
        --timeout=90s || true
    
    echo "✅ Ingress controller installed"
}

# Create namespace and deploy
deploy() {
    echo ""
    echo "Deploying IntelliWeather..."
    
    # Create namespace
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secrets (using defaults for local dev)
    kubectl create secret generic intelliweather-secrets \
        --namespace ${NAMESPACE} \
        --from-literal=secret-key="local-dev-secret-key-change-in-prod" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply manifests
    kubectl apply -f "$(dirname "$0")/deployment.yaml" --namespace ${NAMESPACE}
    
    echo "Waiting for pods to be ready..."
    kubectl wait --namespace ${NAMESPACE} \
        --for=condition=ready pod \
        --selector=app=intelliweather \
        --timeout=120s || true
    
    echo "✅ Deployment complete"
}

# Port forward
port_forward() {
    echo ""
    echo "Setting up port forwarding..."
    echo "Access the application at: http://localhost:8080"
    echo "Press Ctrl+C to stop"
    echo ""
    
    kubectl port-forward --namespace ${NAMESPACE} svc/intelliweather 8080:80
}

# Show status
status() {
    echo ""
    echo "📊 Cluster Status"
    echo "=================="
    
    echo ""
    echo "Pods:"
    kubectl get pods --namespace ${NAMESPACE} -o wide
    
    echo ""
    echo "Services:"
    kubectl get svc --namespace ${NAMESPACE}
    
    echo ""
    echo "Ingress:"
    kubectl get ingress --namespace ${NAMESPACE}
    
    echo ""
    echo "HPA:"
    kubectl get hpa --namespace ${NAMESPACE}
}

# Cleanup
cleanup() {
    echo ""
    echo "Cleaning up..."
    
    kind delete cluster --name ${CLUSTER_NAME}
    
    echo "✅ Cluster deleted"
}

# Main
case "${1:-}" in
    setup)
        check_deps
        create_cluster
        build_image
        install_ingress
        deploy
        status
        echo ""
        echo "🎉 Setup complete! Run './local-setup.sh forward' to access the app"
        ;;
    forward)
        port_forward
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    build)
        build_image
        ;;
    deploy)
        deploy
        ;;
    *)
        echo "Usage: $0 {setup|forward|status|cleanup|build|deploy}"
        echo ""
        echo "Commands:"
        echo "  setup   - Full setup: create cluster, build image, deploy"
        echo "  forward - Port forward to access the application"
        echo "  status  - Show cluster status"
        echo "  cleanup - Delete the cluster"
        echo "  build   - Build and load Docker image"
        echo "  deploy  - Deploy to existing cluster"
        exit 1
        ;;
esac
