#!/bin/bash

# YuYu Lolita Shopping - Codespaces Development Startup Script
# This script starts both API and Web applications in GitHub Codespaces

set -e  # Exit on any error

echo "🌐 Starting YuYu Lolita Shopping in GitHub Codespaces..."
echo "📍 Environment: GitHub Codespaces"
echo "📂 Working directory: $(pwd)"
echo ""

# Check if .env file exists (should be copied from .env.codespaces)
if [ ! -f ".env" ]; then
    echo "📝 Copying Codespaces environment configuration..."
    if [ -f ".env.codespaces" ]; then
        cp .env.codespaces .env
        echo "✅ Environment file ready"
    else
        echo "❌ .env.codespaces not found!"
        exit 1
    fi
fi

# Check if dependencies are installed
echo "📦 Checking dependencies..."
if [ ! -d "node_modules" ]; then
    echo "📥 Installing dependencies..."
    bun install
else
    echo "✅ Dependencies already installed"
fi

# Check PostgreSQL connection
echo "🗄️  Checking database connection..."
if sudo -u postgres psql -d yuyu_lolita -c "SELECT 1;" &> /dev/null; then
    echo "✅ Database connection successful"
else
    echo "⚠️  Database not ready. Setting up PostgreSQL..."
    ./scripts/setup-postgres-codespaces.sh
fi

# Function to get Codespaces URL
get_codespaces_url() {
    local port=$1
    if [ -n "$CODESPACE_NAME" ] && [ -n "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN" ]; then
        echo "https://${CODESPACE_NAME}-${port}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    else
        echo "http://localhost:${port}"
    fi
}

# Update environment variables with actual Codespaces URLs
if [ -n "$CODESPACE_NAME" ] && [ -n "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN" ]; then
    echo "🔧 Updating environment for Codespaces URLs..."
    
    # Get the URLs
    API_URL=$(get_codespaces_url 3001)
    WEB_URL=$(get_codespaces_url 5173)
    
    # Update .env file with actual URLs
    sed -i "s|PUBLIC_API_URL=.*|PUBLIC_API_URL=${API_URL}|g" .env
    sed -i "s|CORS_ORIGIN=.*|CORS_ORIGIN=${WEB_URL},${API_URL},http://localhost:5173,http://localhost:3001|g" .env
    
    echo "✅ URLs updated:"
    echo "   🌐 Web App: ${WEB_URL}"
    echo "   🚀 API: ${API_URL}"
    echo "   📚 API Docs: ${API_URL}/swagger"
fi

echo ""
echo "🚀 Starting applications..."

# Function to start API server
start_api() {
    echo "🔄 Starting API server..."
    cd apps/api
    exec bun --hot src/index-db.ts
}

# Function to start Web app
start_web() {
    echo "🔄 Starting Web application..."
    cd apps/web
    exec bun run dev -- --host 0.0.0.0 --port 5173
}

# Start both services in background
echo "📡 Starting API server on port 3001..."
start_api &
API_PID=$!

echo "🌐 Starting Web app on port 5173..."
start_web &
WEB_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $API_PID $WEB_PID 2>/dev/null || true
    exit 0
}

# Setup signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🎉 YuYu Lolita Shopping is starting up!"
echo ""
echo "📱 Access your application:"
if [ -n "$CODESPACE_NAME" ]; then
    echo "   🌐 Web App: $(get_codespaces_url 5173)"
    echo "   🚀 API: $(get_codespaces_url 3001)"
    echo "   📚 API Documentation: $(get_codespaces_url 3001)/swagger"
else
    echo "   🌐 Web App: http://localhost:5173"
    echo "   🚀 API: http://localhost:3001"
    echo "   📚 API Documentation: http://localhost:3001/swagger"
fi
echo ""
echo "💡 The applications will automatically reload when you make changes"
echo "🛑 Press Ctrl+C to stop both services"
echo ""

# Wait for both processes
wait $API_PID $WEB_PID