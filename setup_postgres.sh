#!/bin/bash
# PostgreSQL Setup Script for IntelliWeather

set -e

echo "🐘 Setting up PostgreSQL for IntelliWeather..."

# Start PostgreSQL service
sudo service postgresql start

# Create user and database (will skip if already exists)
sudo -u postgres psql -c "CREATE USER intelliweather WITH PASSWORD 'intelliweather123';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "CREATE DATABASE intelliweather OWNER intelliweather;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE intelliweather TO intelliweather;" 2>/dev/null || true

# Create tables
echo "📊 Creating database tables..."
PGPASSWORD=intelliweather123 psql -h localhost -U intelliweather -d intelliweather << 'EOF'
-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    subscription_tier VARCHAR(20) DEFAULT 'free'
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_valid BOOLEAN DEFAULT TRUE
);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    hashed_key TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_per_minute INTEGER DEFAULT 60,
    subscription_tier VARCHAR(20) DEFAULT 'free'
);

-- Search History table
CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    lat DECIMAL(10,8) NOT NULL,
    lon DECIMAL(11,8) NOT NULL,
    searched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    api_key_id UUID REFERENCES api_keys(key_id) ON DELETE SET NULL,
    endpoint VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    status_code INTEGER
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_id ON usage_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_timestamp ON usage_tracking(timestamp);

-- Insert test users
INSERT INTO users (username, email, hashed_password) VALUES
    ('admin', 'admin@test.com', '$2b$12$GqXqX4n3gTqzxDl8.d6vru2KkHZj8j4vUHRjnWFJ5rL2J8J5J5J5J'),
    ('user', 'user@test.com', '$2b$12$GqXqX4n3gTqzxDl8.d6vru2KkHZj8j4vUHRjnWFJ5rL2J8J5J5J5J'),
    ('demo', 'demo@test.com', '$2b$12$GqXqX4n3gTqzxDl8.d6vru2KkHZj8j4vUHRjnWFJ5rL2J8J5J5J5J')
ON CONFLICT (email) DO NOTHING;

EOF

echo "✅ PostgreSQL setup complete!"
echo ""
echo "🔑 Database credentials:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: intelliweather"
echo "  Username: intelliweather"
echo "  Password: intelliweather123"
echo ""
echo "👤 Test users created with password 'Admin123!':"
echo "  admin@test.com"
echo "  user@test.com"  
echo "  demo@test.com"