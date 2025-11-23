"""
Database Manager - Abstraction layer for SQLite and PostgreSQL
Supports both databases with a unified interface for thread-safe operations
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Database type from environment (defaults to sqlite for backward compatibility)
DB_TYPE = os.environ.get("DB_TYPE", "sqlite").lower()

# SQLite imports
import sqlite3

# PostgreSQL imports (optional - only if using PostgreSQL)
try:
    import psycopg2
    from psycopg2.extras import RealDictRow
    from psycopg2.pool import ThreadedConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    if DB_TYPE == "postgresql":
        print("⚠️  PostgreSQL selected but psycopg2 not installed. Run: pip install psycopg2-binary")

# Database configuration
if DB_TYPE == "postgresql":
    DB_CONFIG = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "database": os.environ.get("DB_NAME", "fall_detection"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
    }
    # Connection pool for PostgreSQL (thread-safe)
    DB_POOL = None
else:
    # SQLite configuration
    DB_PATH = os.environ.get("DB_PATH", "system_config.db")
    DB_POOL = None  # SQLite doesn't use connection pooling

class DatabaseRow:
    """Wrapper to make both SQLite Row and PostgreSQL RealDictRow behave the same"""
    def __init__(self, row, cursor=None):
        if isinstance(row, dict):
            self._data = row
        elif hasattr(row, 'keys'):  # SQLite Row or RealDictRow
            self._data = dict(row)
        else:
            # Convert tuple to dict using column names
            if cursor:
                columns = [desc[0] for desc in cursor.description]
                self._data = dict(zip(columns, row))
            else:
                self._data = {}
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __contains__(self, key):
        return key in self._data
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def keys(self):
        return self._data.keys()
    
    def __iter__(self):
        return iter(self._data)
    
    def __repr__(self):
        return repr(self._data)

def get_db_connection():
    """
    Create a new database connection (thread-safe)
    Returns a connection object that works with both SQLite and PostgreSQL
    """
    global DB_POOL
    
    if DB_TYPE == "postgresql":
        if not PSYCOPG2_AVAILABLE:
            print("❌ PostgreSQL requested but psycopg2 not available")
            return None
        
        # Initialize connection pool if not exists
        if DB_POOL is None:
            try:
                DB_POOL = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    **DB_CONFIG
                )
                print("✅ PostgreSQL connection pool initialized")
            except Exception as e:
                print(f"❌ Failed to create PostgreSQL connection pool: {e}")
                return None
        
        try:
            conn = DB_POOL.getconn()
            return conn
        except Exception as e:
            print(f"❌ Failed to get PostgreSQL connection: {e}")
            return None
    else:
        # SQLite (per-operation connection for thread safety)
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ SQLite connection error: {e}")
            return None

def close_db_connection(conn):
    """Close database connection (returns to pool for PostgreSQL)"""
    if not conn:
        return
    
    if DB_TYPE == "postgresql" and DB_POOL:
        try:
            DB_POOL.putconn(conn)
        except Exception as e:
            print(f"⚠️  Error returning connection to pool: {e}")
            try:
                conn.close()
            except:
                pass
    else:
        # SQLite - just close
        try:
            conn.close()
        except:
            pass

def execute_query(conn, query, params=None, fetch_one=False, fetch_all=False):
    """
    Execute a query and return results
    Works with both SQLite and PostgreSQL parameter styles
    """
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Convert SQLite-style ? parameters to PostgreSQL-style %s if needed
        if DB_TYPE == "postgresql" and params:
            # PostgreSQL uses %s instead of ?
            query = query.replace('?', '%s')
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            row = cursor.fetchone()
            if row:
                if DB_TYPE == "postgresql":
                    return DatabaseRow(dict(row), cursor)
                else:
                    return DatabaseRow(row, cursor)
            return None
        elif fetch_all:
            rows = cursor.fetchall()
            if DB_TYPE == "postgresql":
                return [DatabaseRow(dict(row), cursor) for row in rows]
            else:
                return [DatabaseRow(row, cursor) for row in rows]
        else:
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        print(f"❌ Query execution error: {e}")
        print(f"   Query: {query[:100]}...")
        conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()

def init_database():
    """Initialize database tables (works with both SQLite and PostgreSQL)"""
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to initialize database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # SQL syntax differences
        if DB_TYPE == "postgresql":
            # PostgreSQL uses SERIAL instead of INTEGER PRIMARY KEY AUTOINCREMENT
            auto_increment = "SERIAL PRIMARY KEY"
            text_type = "TEXT"
            integer_type = "INTEGER"
            real_type = "REAL"
        else:
            # SQLite
            auto_increment = "INTEGER PRIMARY KEY AUTOINCREMENT"
            text_type = "TEXT"
            integer_type = "INTEGER"
            real_type = "REAL"
        
        # Users table
        users_table = f'''CREATE TABLE IF NOT EXISTS users (
            id {text_type} PRIMARY KEY,
            name {text_type} NOT NULL,
            email {text_type} UNIQUE,
            phone {text_type} UNIQUE,
            password_hash {text_type},
            is_sso {integer_type} DEFAULT 0,
            twofa_secret {text_type},
            is_2fa_enabled {integer_type} DEFAULT 0,
            recovery_key {text_type},
            role {text_type} DEFAULT 'patient',
            created_at {text_type}
        )'''
        cursor.execute(users_table)
        
        # Falls table
        falls_table = f'''CREATE TABLE IF NOT EXISTS falls (
            id {auto_increment},
            user_id {text_type} NOT NULL,
            timestamp {text_type} NOT NULL,
            status {text_type} NOT NULL,
            details {text_type},
            alert_sent {integer_type} DEFAULT 0,
            video_path {text_type},
            severity {text_type} DEFAULT 'moderate',
            location {text_type},
            response_time_seconds {real_type},
            FOREIGN KEY(user_id) REFERENCES users(id)
        )'''
        cursor.execute(falls_table)
        
        # Patient-Caretaker relationships
        patient_caretaker_table = f'''CREATE TABLE IF NOT EXISTS patient_caretaker (
            id {auto_increment},
            patient_id {text_type} NOT NULL,
            caretaker_id {text_type} NOT NULL,
            assigned_by {text_type},
            assigned_at {text_type},
            is_active {integer_type} DEFAULT 1,
            FOREIGN KEY(patient_id) REFERENCES users(id),
            FOREIGN KEY(caretaker_id) REFERENCES users(id),
            UNIQUE(patient_id, caretaker_id)
        )'''
        cursor.execute(patient_caretaker_table)
        
        # User cameras
        cameras_table = f'''CREATE TABLE IF NOT EXISTS user_cameras (
            id {auto_increment},
            user_id {text_type} NOT NULL,
            camera_url_or_index {text_type} NOT NULL,
            camera_name {text_type},
            location {text_type},
            is_active {integer_type} DEFAULT 1,
            created_at {text_type},
            FOREIGN KEY(user_id) REFERENCES users(id)
        )'''
        cursor.execute(cameras_table)
        
        # Fall reviews
        reviews_table = f'''CREATE TABLE IF NOT EXISTS fall_reviews (
            id {auto_increment},
            fall_id {integer_type} NOT NULL,
            reviewed_by {text_type} NOT NULL,
            review_status {text_type} NOT NULL,
            review_notes {text_type},
            reviewed_at {text_type},
            FOREIGN KEY(fall_id) REFERENCES falls(id),
            FOREIGN KEY(reviewed_by) REFERENCES users(id)
        )'''
        cursor.execute(reviews_table)
        
        conn.commit()
        print(f"✅ Database tables initialized ({DB_TYPE.upper()})")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        close_db_connection(conn)

def get_lastrowid(cursor):
    """Get the last inserted row ID (works with both databases)"""
    if DB_TYPE == "postgresql":
        return cursor.fetchone()[0] if cursor else None
    else:
        return cursor.lastrowid if cursor else None

# Context manager for database operations
class DBConnection:
    """Context manager for database connections"""
    def __init__(self):
        self.conn = None
    
    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            close_db_connection(self.conn)
        return False


