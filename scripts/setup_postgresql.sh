#!/bin/bash
# PostgreSQL Setup Script for Fall Detection System
# This script helps set up PostgreSQL for the fall detection application

set -e

echo "=========================================="
echo "PostgreSQL Setup for Fall Detection"
echo "=========================================="
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Installing via Homebrew..."
    brew install postgresql@14
fi

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL not running. Starting service..."
    brew services start postgresql@14
    sleep 3
fi

# Check if database exists
if psql -lqt | cut -d \| -f 1 | grep -qw fall_detection; then
    echo "✅ Database 'fall_detection' already exists"
else
    echo "📦 Creating database 'fall_detection'..."
    createdb fall_detection
    echo "✅ Database created"
fi

# Check if user exists
if psql -d fall_detection -tc "SELECT 1 FROM pg_roles WHERE rolname='fall_user'" | grep -q 1; then
    echo "✅ User 'fall_user' already exists"
else
    echo "👤 Creating user 'fall_user'..."
    psql -d fall_detection -c "CREATE USER fall_user WITH PASSWORD 'fall_detection_2024';"
    psql -d fall_detection -c "GRANT ALL PRIVILEGES ON DATABASE fall_detection TO fall_user;"
    psql -d fall_detection -c "ALTER DATABASE fall_detection OWNER TO fall_user;"
    echo "✅ User created with privileges"
fi

# Install Python package
echo "📦 Installing psycopg2-binary..."
pip3 install -q psycopg2-binary || pip install -q psycopg2-binary
echo "✅ Python package installed"

# Test connection
echo ""
echo "🧪 Testing connection..."
python3 << EOF
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import get_db_connection, close_db_connection

os.environ['DB_TYPE'] = 'postgresql'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'fall_detection'
os.environ['DB_USER'] = 'fall_user'
os.environ['DB_PASSWORD'] = 'fall_detection_2024'

conn = get_db_connection()
if conn:
    print("✅ Connection test successful!")
    close_db_connection(conn)
    sys.exit(0)
else:
    print("❌ Connection test failed!")
    sys.exit(1)
EOF

echo ""
echo "=========================================="
echo "✅ PostgreSQL setup complete!"
echo "=========================================="
echo ""
echo "📝 Next steps:"
echo "   1. Add these lines to your .env file:"
echo ""
echo "      DB_TYPE=postgresql"
echo "      DB_HOST=localhost"
echo "      DB_PORT=5432"
echo "      DB_NAME=fall_detection"
echo "      DB_USER=fall_user"
echo "      DB_PASSWORD=fall_detection_2024"
echo ""
echo "   2. Restart your Flask application"
echo "   3. The system will automatically create all tables"
echo ""

