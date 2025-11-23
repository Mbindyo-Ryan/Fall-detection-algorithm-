# Database Migration Guide: SQLite to PostgreSQL

This guide explains how to migrate from SQLite to PostgreSQL for better thread-safety and production readiness.

## Why PostgreSQL?

- **Thread-Safe**: Native support for concurrent connections
- **Production-Ready**: Better performance and reliability
- **Scalability**: Handles high concurrent load
- **Connection Pooling**: Efficient resource management

## Quick Start

### Option 1: Keep SQLite (Default - No Changes Needed)

The system defaults to SQLite. Just run as normal:

```bash
python3 app_auth.py
```

### Option 2: Switch to PostgreSQL

1. **Install PostgreSQL** (if not already installed):

   **macOS:**
   ```bash
   brew install postgresql@14
   brew services start postgresql@14
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

   **Windows:**
   Download from https://www.postgresql.org/download/windows/

2. **Create Database and User:**

   ```bash
   # Login as postgres user
   sudo -u postgres psql
   
   # Create database and user
   CREATE DATABASE fall_detection;
   CREATE USER fall_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE fall_detection TO fall_user;
   \q
   ```

3. **Install Python Dependencies:**

   ```bash
   pip install psycopg2-binary
   ```

4. **Configure Environment Variables:**

   Create or update your `.env` file:

   ```bash
   # Database Configuration
   DB_TYPE=postgresql
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=fall_detection
   DB_USER=fall_user
   DB_PASSWORD=your_secure_password
   
   # Keep your existing config
   FLASK_SECRET=your_secret_key
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

5. **Run the Application:**

   ```bash
   python3 app_auth.py
   ```

   The system will automatically:
   - Connect to PostgreSQL
   - Create all necessary tables
   - Migrate your data (if using migration script)

## Migration Script (Optional)

If you have existing SQLite data, use the migration script:

```bash
python3 scripts/migrate_to_postgresql.py
```

This script will:
1. Read all data from SQLite
2. Connect to PostgreSQL
3. Create tables
4. Copy all data
5. Verify migration

## Architecture

### Database Abstraction Layer

The new `db_manager.py` provides:

- **Unified Interface**: Same code works with both SQLite and PostgreSQL
- **Thread-Safe Connections**: Proper connection pooling for PostgreSQL
- **Automatic Parameter Conversion**: Handles SQLite `?` vs PostgreSQL `%s`
- **Error Handling**: Graceful fallbacks and error messages

### Connection Management

- **SQLite**: Per-operation connections (thread-safe pattern)
- **PostgreSQL**: Connection pool (1-20 connections, managed automatically)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_TYPE` | `sqlite` | Database type: `sqlite` or `postgresql` |
| `DB_PATH` | `system_config.db` | SQLite database file path |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `fall_detection` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL username |
| `DB_PASSWORD` | (empty) | PostgreSQL password |

## Code Changes

### Before (SQLite only):

```python
import sqlite3
conn = sqlite3.connect("system_config.db")
c = conn.cursor()
c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
row = c.fetchone()
conn.close()
```

### After (Works with both):

```python
from db_manager import get_db_connection, close_db_connection

conn = get_db_connection()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
finally:
    close_db_connection(conn)
```

## Troubleshooting

### PostgreSQL Connection Failed

**Error**: `❌ Failed to create PostgreSQL connection pool`

**Solutions**:
1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Verify credentials in `.env` file
3. Check firewall: `sudo ufw allow 5432`
4. Test connection: `psql -h localhost -U fall_user -d fall_detection`

### psycopg2 Not Found

**Error**: `PostgreSQL selected but psycopg2 not installed`

**Solution**:
```bash
pip install psycopg2-binary
```

### Migration Issues

If migration fails:
1. Check PostgreSQL logs: `/var/log/postgresql/postgresql-*.log`
2. Verify table structure matches
3. Check foreign key constraints
4. Run migration in transaction mode

## Performance Comparison

| Operation | SQLite | PostgreSQL |
|----------|--------|-------------|
| Single User | Fast | Fast |
| Concurrent Users | Slower | Fast |
| Thread Safety | Manual | Native |
| Connection Pooling | No | Yes |
| Production Ready | Limited | Yes |

## Recommendations

- **Development**: Use SQLite (default, no setup needed)
- **Testing**: Use SQLite or PostgreSQL (your choice)
- **Production**: Use PostgreSQL (better performance and reliability)

## Rollback

To switch back to SQLite:

1. Update `.env`:
   ```bash
   DB_TYPE=sqlite
   DB_PATH=system_config.db
   ```

2. Restart the application

Your data will remain in PostgreSQL (not deleted), but the app will use SQLite.

## Support

For issues or questions:
1. Check server console logs
2. Review PostgreSQL logs
3. Run `python3 scripts/debug_falls.py` to check database status
4. Verify environment variables are set correctly


