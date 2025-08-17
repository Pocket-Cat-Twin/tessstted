#!/bin/bash

# PostgreSQL Setup Script for GitHub Codespaces
# This script sets up PostgreSQL in GitHub Codespaces environment

set -e  # Exit on any error

echo "🚀 Setting up PostgreSQL for GitHub Codespaces..."

# Check if PostgreSQL is already installed
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL is already installed"
else
    echo "📦 Installing PostgreSQL..."
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-contrib
fi

# Check if PostgreSQL service is running
if sudo systemctl is-active --quiet postgresql; then
    echo "✅ PostgreSQL service is already running"
else
    echo "🔄 Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

# Setup database and user
echo "🔧 Setting up database and user..."

# Switch to postgres user and setup
sudo -u postgres psql << EOF
-- Create database if it doesn't exist
SELECT 'CREATE DATABASE yuyu_lolita' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'yuyu_lolita');
\gexec

-- Ensure postgres user has proper permissions
ALTER USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE yuyu_lolita TO postgres;

-- Show current databases
\l
EOF

# Test connection
echo "🧪 Testing database connection..."
if sudo -u postgres psql -d yuyu_lolita -c "SELECT 1;" &> /dev/null; then
    echo "✅ Database connection successful!"
else
    echo "❌ Database connection failed!"
    exit 1
fi

# Copy Codespaces environment file
echo "📝 Setting up environment file..."
if [ -f ".env.codespaces" ]; then
    cp .env.codespaces .env
    echo "✅ Environment file (.env) updated for Codespaces"
else
    echo "❌ .env.codespaces file not found!"
    exit 1
fi

# Install dependencies if not already installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    bun install
fi

echo ""
echo "🎉 PostgreSQL setup completed!"
echo "📊 Database: yuyu_lolita"
echo "👤 User: postgres"
echo "🔑 Password: postgres"
echo "📡 Connection: Unix socket (/var/run/postgresql)"
echo ""
echo "Next steps:"
echo "1. Run migrations: bun run db:migrate:codespaces"
echo "2. Seed database: bun run db:seed:codespaces"
echo "3. Start development: bun run dev:codespaces"