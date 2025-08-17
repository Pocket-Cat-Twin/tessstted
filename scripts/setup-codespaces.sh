#!/bin/bash

# YuYu Lolita Shopping - Complete Codespaces Setup Script
# This script performs complete setup for GitHub Codespaces environment

set -e  # Exit on any error

echo "🚀 YuYu Lolita Shopping - GitHub Codespaces Setup"
echo "=================================================="
echo ""

# Display environment info
echo "🔍 Environment Information:"
echo "   📍 Codespace: ${CODESPACE_NAME:-'Not detected'}"
echo "   🌐 Domain: ${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-'Not available'}"
echo "   🖥️  Platform: $(uname -s)"
echo "   📂 Directory: $(pwd)"
echo ""

# Step 1: Setup environment file
echo "📝 Step 1: Setting up environment configuration..."
if [ -f ".env.codespaces" ]; then
    cp .env.codespaces .env
    echo "✅ Environment file configured for Codespaces"
else
    echo "❌ .env.codespaces file not found!"
    exit 1
fi

# Step 2: Install dependencies
echo ""
echo "📦 Step 2: Installing dependencies..."
if command -v bun &> /dev/null; then
    echo "✅ Bun is available"
    bun install
    echo "✅ Dependencies installed"
else
    echo "⚠️  Bun not found, trying with npm..."
    npm install
fi

# Step 3: Setup PostgreSQL
echo ""
echo "🗄️  Step 3: Setting up PostgreSQL..."
chmod +x scripts/setup-postgres-codespaces.sh
./scripts/setup-postgres-codespaces.sh

# Step 4: Run database migrations
echo ""
echo "🔄 Step 4: Running database migrations..."
if [ -d "packages/db" ]; then
    cd packages/db
    if bun run migrate; then
        echo "✅ Database migrations completed"
    else
        echo "⚠️  Migrations failed, but continuing..."
    fi
    cd ../..
else
    echo "⚠️  Database package not found, skipping migrations"
fi

# Step 5: Seed database (optional)
echo ""
echo "🌱 Step 5: Seeding database..."
if [ -d "packages/db" ]; then
    cd packages/db
    if bun run seed; then
        echo "✅ Database seeded successfully"
    else
        echo "⚠️  Seeding failed, but continuing..."
    fi
    cd ../..
fi

# Step 6: Build applications
echo ""
echo "🏗️  Step 6: Building applications..."
if bun run build; then
    echo "✅ Applications built successfully"
else
    echo "⚠️  Build failed, but continuing..."
fi

# Step 7: Setup permissions
echo ""
echo "🔐 Step 7: Setting up permissions..."
chmod +x scripts/start-codespaces.sh
chmod +x scripts/auto-start.js

# Display final information
echo ""
echo "🎉 Setup completed successfully!"
echo "================================"
echo ""
echo "📱 Next steps:"
echo "   1. Start development: bun run dev:codespaces"
echo "   2. Or use auto-detection: bun run dev:auto"
echo ""
echo "🌐 Your application will be available at:"
if [ -n "$CODESPACE_NAME" ] && [ -n "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN" ]; then
    echo "   🌐 Web App: https://${CODESPACE_NAME}-5173.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo "   🚀 API: https://${CODESPACE_NAME}-3001.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo "   📚 API Docs: https://${CODESPACE_NAME}-3001.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/swagger"
else
    echo "   🌐 Web App: http://localhost:5173"
    echo "   🚀 API: http://localhost:3001"
    echo "   📚 API Docs: http://localhost:3001/swagger"
fi
echo ""
echo "💡 Tips:"
echo "   - Applications will auto-reload on changes"
echo "   - Use 'bun run dev:auto' for automatic environment detection"
echo "   - Check port visibility in Codespaces if you can't access the app"
echo "   - Original Windows commands still work: bun run dev:windows"