import os
from dotenv import load_dotenv
load_dotenv()
import sqlite3
import secrets
from datetime import datetime, timedelta
import time
from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify
from authlib.integrations.flask_client import OAuth
from functools import wraps

# 2FA imports
import pyotp
import qrcode
from io import BytesIO
import base64

# Import FIXED detection logic
import detection_skeleton
from detection_skeleton import detector, generate_frames_async, init_db as init_fall_db
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory

# =========================================================
# CONFIGURATION
# =========================================================
app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET", "default_secret_key_change_me")
app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID")
app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET")
DB_PATH = "system_config.db"
ORGANIZATION_NAME = "CARE_System"

# Configuration check
print("--- ENVIRONMENT VARIABLE STATUS ---")
if app.secret_key != "default_secret_key_change_me":
    print("✅ FLASK_SECRET: Loaded successfully.")
else:
    print("⚠️ FLASK_SECRET: Using default key. Set environment variable for production!")
if app.config.get("GOOGLE_CLIENT_ID"):
    print("✅ GOOGLE_CLIENT_ID: Loaded successfully.")
else:
    print("❌ GOOGLE_CLIENT_ID: NOT FOUND. Google SSO will fail.")
if app.config.get("GOOGLE_CLIENT_SECRET"):
    print("✅ GOOGLE_CLIENT_SECRET: Loaded successfully.")
else:
    print("❌ GOOGLE_CLIENT_SECRET: NOT FOUND. Google SSO will fail.")
print("-----------------------------------")

# =========================================================
# OAUTH INITIALIZATION
# =========================================================
oauth = OAuth(app)
if app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"]:
    oauth.register(
        name='google',
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    print("✅ Google OAuth configured successfully")
else:
    print("❌ Google OAuth NOT configured - missing credentials")

# =========================================================
# DATABASE CONNECTION MANAGEMENT
# =========================================================
def get_db_connection():
    """Create a new database connection for each request (Thread-Safe)"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"❌ Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables on application start"""
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to initialize database")
        return

    try:
        c = conn.cursor()
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE,
                        phone TEXT UNIQUE,
                        password_hash TEXT,
                        is_sso INTEGER DEFAULT 0,
                        twofa_secret TEXT,
                        is_2fa_enabled INTEGER DEFAULT 0,
                        recovery_key TEXT,
                        role TEXT DEFAULT 'patient',
                        created_at TEXT
                    )''')
        
        # Add role column if it doesn't exist (migration)
        try:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'patient'")
            print("✅ 'role' column added to users table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"⚠️ Error adding role column: {e}")
        
        # Update existing users without role to 'patient'
        c.execute("UPDATE users SET role = 'patient' WHERE role IS NULL")
        
        # Patient-Caretaker relationships
        c.execute('''CREATE TABLE IF NOT EXISTS patient_caretaker (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id TEXT NOT NULL,
                        caretaker_id TEXT NOT NULL,
                        assigned_by TEXT,
                        assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1,
                        FOREIGN KEY (patient_id) REFERENCES users (id),
                        FOREIGN KEY (caretaker_id) REFERENCES users (id),
                        UNIQUE(patient_id, caretaker_id)
                    )''')
        
        # Patient-Doctor relationships
        c.execute('''CREATE TABLE IF NOT EXISTS patient_doctor (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id TEXT NOT NULL,
                        doctor_id TEXT NOT NULL,
                        assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1,
                        FOREIGN KEY (patient_id) REFERENCES users (id),
                        FOREIGN KEY (doctor_id) REFERENCES users (id),
                        UNIQUE(patient_id, doctor_id)
                    )''')
        
        # Emergency contacts
        c.execute('''CREATE TABLE IF NOT EXISTS emergency_contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        contact_name TEXT NOT NULL,
                        contact_phone TEXT NOT NULL,
                        contact_email TEXT,
                        relationship TEXT,
                        priority INTEGER DEFAULT 1,
                        is_active INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''')

        # User cameras table
        c.execute('''CREATE TABLE IF NOT EXISTS user_cameras (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        camera_name TEXT NOT NULL,
                        camera_url_or_index TEXT NOT NULL,
                        location TEXT,
                        is_active INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''')

        # Fall reviews table (doctor reviews and recommendations)
        c.execute('''CREATE TABLE IF NOT EXISTS fall_reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fall_id INTEGER NOT NULL,
                        doctor_id TEXT NOT NULL,
                        review_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        remarks TEXT,
                        recommendations TEXT,
                        recommended_actions TEXT,  -- JSON: ["xray", "physiotherapy", "consultation"]
                        follow_up_date TEXT,
                        status TEXT DEFAULT 'pending',  -- pending, reviewed, completed
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (fall_id) REFERENCES falls (id),
                        FOREIGN KEY (doctor_id) REFERENCES users (id)
                    )''')

        # Fall files table (uploaded documents, X-rays, scans)
        c.execute('''CREATE TABLE IF NOT EXISTS fall_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fall_id INTEGER NOT NULL,
                        review_id INTEGER,
                        uploaded_by TEXT NOT NULL,  -- user_id who uploaded
                        file_name TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_type TEXT,  -- xray, scan, report, other
                        file_size INTEGER,
                        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (fall_id) REFERENCES falls (id),
                        FOREIGN KEY (review_id) REFERENCES fall_reviews (id),
                        FOREIGN KEY (uploaded_by) REFERENCES users (id)
                    )''')

        # File comments table (doctor comments on uploaded files)
        c.execute('''CREATE TABLE IF NOT EXISTS file_comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        doctor_id TEXT NOT NULL,
                        comment TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file_id) REFERENCES fall_files (id),
                        FOREIGN KEY (doctor_id) REFERENCES users (id)
                    )''')

        conn.commit()
        print("✅ Database tables initialized successfully.")

        # Initialize fall detection database
        users = get_users_for_detection(conn)
        init_fall_db(DB_PATH, users)

    except sqlite3.Error as e:
        print(f"❌ Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

def get_users_for_detection(db_conn):
    """Fetch user details for detection module"""
    if not db_conn:
        return []

    try:
        c = db_conn.cursor()
        c.execute("SELECT id, name, email FROM users")
        users = c.fetchall()
        return [dict(user) for user in users]
    except sqlite3.Error as e:
        print(f"Error getting users for detection: {e}")
        return []

def get_user_by_identifier(identifier):
    """Get user by email or phone"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? OR phone = ? OR id = ?", 
                 (identifier, identifier, identifier))
        user = c.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Error getting user: {e}")
        return None
    finally:
        conn.close()

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Error getting user by email: {e}")
        return None
    finally:
        conn.close()

def insert_user(user_data):
    """Insert new user with role"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO users 
                    (id, name, email, phone, password_hash, is_sso, twofa_secret, 
                     is_2fa_enabled, recovery_key, role, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", user_data)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"Error inserting user: {e}")
        return False
    finally:
        conn.close()

# Initialize database on app start
init_database()

# =========================================================
# CAMERA MANAGEMENT
# =========================================================
def get_user_camera(user_id, camera_index=0):
    """Get camera configuration for specific user"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM user_cameras WHERE user_id = ? AND is_active = 1 ORDER BY id LIMIT 1 OFFSET ?",
            (user_id, camera_index)
        )
        camera = c.fetchone()
        return dict(camera) if camera else None
    except sqlite3.Error as e:
        print(f"Error getting user camera: {e}")
        return None
    finally:
        conn.close()

def setup_default_user_camera(user_id, user_name):
    """Setup default camera for new users"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        c = conn.cursor()
        c.execute("SELECT id FROM user_cameras WHERE user_id = ? AND camera_name = ?", 
                 (user_id, "Default Camera"))
        if c.fetchone():
            print(f"ℹ️ Default camera already exists for user {user_name}")
            return True

        c.execute(
            "INSERT INTO user_cameras (user_id, camera_name, camera_url_or_index, location) VALUES (?, ?, ?, ?)",
            (user_id, "Default Camera", "0", "Living Room")
        )
        conn.commit()
        print(f"✅ Default camera setup for user {user_name}")
        return True
    except sqlite3.Error as e:
        print(f"Error setting up default camera: {e}")
        return False
    finally:
        conn.close()

# =========================================================
# DECORATORS
# =========================================================
def login_required(f):
    """Check if user is authenticated"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index', error="Please sign in to access the dashboard."))
        return f(*args, **kwargs)
    return decorated_function

def twofa_required(f):
    """Check if user has passed 2FA verification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_2fa_verified'):
            return f(*args, **kwargs)

        user_row = get_user_by_identifier(session.get('user_id'))
        if user_row and user_row['is_2fa_enabled'] == 1:
            return redirect(url_for('twofa_verification'))
        return f(*args, **kwargs)
    return decorated_function

# =========================================================
# AUTHENTICATION ROUTES
# =========================================================
@app.route("/", methods=["GET", "POST"])
def index():
    """Login/Auth entry point"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        identifier = request.form.get("identifier")
        password = request.form.get("password")

        user_row = get_user_by_identifier(identifier)
        if user_row and user_row['is_sso'] == 0:
            user_id = user_row['id']
            name = user_row['name']
            password_hash = user_row['password_hash']
            is_2fa_enabled = user_row['is_2fa_enabled']

            if password_hash and check_password_hash(password_hash, password):
                session['user_id'] = user_id
                session['user_name'] = name
                session['user_role'] = user_row['role'] if 'role' in user_row.keys() and user_row['role'] else 'patient'
                session['is_2fa_verified'] = False

                if is_2fa_enabled == 1:
                    return redirect(url_for('twofa_verification'))
                else:
                    return redirect(url_for('setup_2fa'))
            else:
                return render_template("login.html", error="Invalid password.", tab='login')
        else:
            return render_template("login.html", 
                                 error="User not found or cannot log in with password.", 
                                 tab='login')

    error = request.args.get('error')
    reg_message = request.args.get('reg_message')
    tab = request.args.get('tab', 'login')
    return render_template("login.html", error=error, reg_message=reg_message, tab=tab)

@app.route("/register", methods=["POST"])
def register():
    """Handle user registration with role selection"""
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    role = request.form.get("role", "patient")  # Default to patient

    # Validate role
    valid_roles = ['patient', 'doctor', 'caretaker']
    if role not in valid_roles:
        role = 'patient'

    if not all([name, email, phone, password]):
        return redirect(url_for('index', 
                               reg_message="Registration failed: All fields required.", 
                               tab='register'))

    user_id = "local_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    user_data = (user_id, name, email, phone, password_hash, 0, None, 0, None, role,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    if insert_user(user_data):
        setup_default_user_camera(user_id, name)
        return redirect(url_for('index', 
                               reg_message=f"Registration successful as {role.title()}! Please sign in.", 
                               tab='login'))
    else:
        return redirect(url_for('index', 
                               reg_message="Registration failed: Email or Phone already in use.", 
                               tab='register'))

@app.route("/logout", methods=["POST"])
def logout():
    """Log user out"""
    session.clear()
    return redirect(url_for('index', reg_message="You have been successfully signed out."))

# =========================================================
# GOOGLE OAUTH
# =========================================================
@app.route("/login/google", endpoint='login_google')
def login_google():
    """Redirect to Google for authorization"""
    if not oauth.google:
        return redirect(url_for('index', error="Google SSO not configured."))
    
    try:
        redirect_uri = url_for("authorize_google", _external=True)
        print(f"🔧 OAuth redirect URI: {redirect_uri}")
        return oauth.google.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"❌ OAuth redirect error: {e}")
        return redirect(url_for('index', error="Google sign-in configuration error."))

@app.route("/authorize/google", endpoint='authorize_google')
def authorize_google():
    """Handle Google OAuth callback"""
    print("=== GOOGLE OAUTH CALLBACK STARTED ===")
    
    if not oauth.google:
        print("❌ OAuth not configured")
        return redirect(url_for('index', error="Google OAuth not configured on server."))
    
    try:
        print("🔧 Getting access token...")
        token = oauth.google.authorize_access_token()
        print(f"✅ Token received: {bool(token)}")
    except Exception as e:
        print(f"❌ Token error: {e}")
        return redirect(url_for('index', error=f"Google sign-in failed: {str(e)}"))

    try:
        print("🔧 Fetching user info...")
        user_info = oauth.google.userinfo()
        print(f"✅ User info received: {user_info}")
        
    except Exception as e:
        print(f"❌ User info error: {e}")
        return redirect(url_for('index', error="Could not retrieve user info from Google."))

    email = user_info.get('email')
    name = user_info.get('name')
    google_id = user_info.get('sub')

    print(f"🔧 Extracted - Email: {email}, Name: {name}, Google ID: {google_id}")

    if not email:
        print("❌ Missing email")
        return redirect(url_for('index', error="Google sign-in failed: No email provided."))

    user_row = get_user_by_email(email)

    if user_row:
        print(f"✅ Existing user found: {user_row['name']}")
        user_id = user_row['id']
        name = user_row['name']
        is_2fa_enabled = user_row['is_2fa_enabled']
        user_role = user_row['role'] if 'role' in user_row.keys() and user_row['role'] else 'patient'
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_role'] = user_role
        session['is_2fa_verified'] = False

        if is_2fa_enabled == 1:
            return redirect(url_for('twofa_verification'))
        else:
            return redirect(url_for('setup_2fa'))
    else:
        print("🆕 New Google user, creating account...")
        user_id = "google_" + google_id
        # Default Google users to 'patient' role
        user_data = (user_id, name, email, "N/A", None, 1, None, 0, None, 'patient',
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

        if insert_user(user_data):
            setup_default_user_camera(user_id, name)
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_role'] = 'patient'
            session['is_2fa_verified'] = False
            return redirect(url_for('setup_2fa'))
        else:
            return redirect(url_for('index', 
                                  error="Registration via Google failed due to DB error."))

# =========================================================
# 2FA ROUTES
# =========================================================
def generate_qr_code(secret, email):
    """Generate QR code for 2FA"""
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=ORGANIZATION_NAME
    )
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

@app.route("/setup_2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    """Setup 2FA for user"""
    user_id = session['user_id']
    user_row = get_user_by_identifier(user_id)

    if not user_row:
        return redirect(url_for('logout'))

    current_secret = user_row['twofa_secret']
    is_enabled = user_row['is_2fa_enabled']
    current_recovery_key = user_row['recovery_key']
    email = user_row['email']

    if is_enabled == 1:
        session['is_2fa_verified'] = True
        return render_template("twofa_setup.html",
                             success="2FA is already enabled.",
                             qr_code=None,
                             secret=current_secret,
                             recovery_key=current_recovery_key, 
                             is_enabled=True)

    # Generate new secret and recovery key
    secret = current_secret or pyotp.random_base32()
    recovery_key = current_recovery_key or secrets.token_hex(16).upper()

    qr_code_base64 = generate_qr_code(secret, email or user_id)

    if request.method == "POST":
        code = request.form.get("code")

        if not code or len(code) != 6:
            return render_template("twofa_setup.html",
                                 qr_code="data:image/png;base64," + qr_code_base64,
                                 secret=secret,
                                 error="Invalid code format.",
                                 recovery_key=recovery_key)

        totp = pyotp.TOTP(secret)

        if totp.verify(code):
            conn = get_db_connection()
            if not conn:
                return render_template("twofa_setup.html", 
                                     qr_code="data:image/png;base64," + qr_code_base64, 
                                     secret=secret, 
                                     error="Database error.")

            try:
                c = conn.cursor()
                c.execute("UPDATE users SET twofa_secret = ?, is_2fa_enabled = 1, recovery_key = ? WHERE id = ?", 
                         (secret, recovery_key, user_id))
                conn.commit()
                session['is_2fa_verified'] = True
                
                return render_template("twofa_setup.html", 
                                     success="2FA setup successful! Save your recovery key!",
                                     qr_code="data:image/png;base64," + qr_code_base64,
                                     secret=secret,
                                     recovery_key=recovery_key,
                                     is_enabled=True)

            except sqlite3.Error as e:
                print(f"Error updating 2FA: {e}")
                return render_template("twofa_setup.html", 
                                     qr_code="data:image/png;base64," + qr_code_base64, 
                                     secret=secret, 
                                     error="Database error saving 2FA.")
            finally:
                conn.close()
        else:
            # Save temporary secret
            conn = get_db_connection()
            if conn:
                try:
                    c = conn.cursor()
                    c.execute("UPDATE users SET twofa_secret = ?, recovery_key = ? WHERE id = ?", 
                             (secret, recovery_key, user_id))
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Error saving temporary secret: {e}")
                finally:
                    conn.close()

            return render_template("twofa_setup.html",
                                 qr_code="data:image/png;base64," + qr_code_base64,
                                 secret=secret,
                                 recovery_key=recovery_key,
                                 error="Invalid 2FA code. Please try again.")

    # GET request - save temporary secret
    conn = get_db_connection()
    if conn and not current_secret:
        try:
            c = conn.cursor()
            c.execute("UPDATE users SET twofa_secret = ?, recovery_key = ? WHERE id = ?", 
                     (secret, recovery_key, user_id))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error saving temporary secret: {e}")
        finally:
            conn.close()

    return render_template("twofa_setup.html",
                         qr_code="data:image/png;base64," + qr_code_base64,
                         secret=secret,
                         recovery_key=recovery_key)

@app.route("/verify_2fa", methods=["GET", "POST"])
def twofa_verification():
    """Handle 2FA verification"""
    if 'user_id' not in session:
        return redirect(url_for('index', error="Session expired. Please log in again."))

    user_id = session['user_id']
    user_row = get_user_by_identifier(user_id)

    if not user_row:
        return redirect(url_for('logout'))

    secret = user_row['twofa_secret']
    is_enabled = user_row['is_2fa_enabled']

    if is_enabled == 0:
        return redirect(url_for('setup_2fa'))

    if session.get('is_2fa_verified'):
        return redirect(url_for('dashboard'))

    if not secret:
        return redirect(url_for('logout', error="2FA configuration error."))

    if request.method == "POST":
        code = request.form.get("code")

        if not code or len(code) != 6:
            return render_template("verify_2fa.html", error="Please enter the 6-digit code.")

        totp = pyotp.TOTP(secret)

        if totp.verify(code):
            session['is_2fa_verified'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template("verify_2fa.html", error="Invalid 2FA code. Please try again.")

    return render_template("verify_2fa.html")

@app.route("/recover_2fa", methods=["GET", "POST"])
def recover_2fa():
    """2FA recovery using recovery key"""
    if 'user_id' not in session:
        return redirect(url_for('index', error="Please log in first to recover 2FA."))
    if session.get('is_2fa_verified'):
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    user_row = get_user_by_identifier(user_id)

    if not user_row:
        return redirect(url_for('logout'))

    correct_recovery_key = user_row['recovery_key']
    is_enabled = user_row['is_2fa_enabled']

    if request.method == 'POST':
        recovery_key = request.form.get('recovery_key').strip().upper()

        if is_enabled == 0 or not correct_recovery_key:
            return render_template('recover_2fa.html', 
                                 error="2FA is not enabled or no recovery key was saved.")

        if recovery_key == correct_recovery_key:
            conn = get_db_connection()
            if conn:
                try:
                    c = conn.cursor()
                    c.execute('UPDATE users SET is_2fa_enabled = 0, twofa_secret = NULL, recovery_key = NULL WHERE id = ?', 
                             (user_id,))
                    conn.commit()
                    session['is_2fa_verified'] = True
                    print(f"User {user_id} recovered account, 2FA disabled and recovery key burned.")
                    return redirect(url_for('dashboard', 
                                          success="Account recovered. 2FA has been disabled. Please set it up again immediately for security."))
                except sqlite3.Error as e:
                    print(f"Error disabling 2FA during recovery: {e}")
                    return render_template('recover_2fa.html', error="Database error during recovery.")
                finally:
                    conn.close()
            else:
                return render_template('recover_2fa.html', error="Database connection error.")
        else:
            return render_template('recover_2fa.html', error="Invalid recovery key.")

    return render_template('recover_2fa.html')

# =========================================================
# DASHBOARD
# =========================================================
@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard"""
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Guest')

    user_row = get_user_by_identifier(user_id)
    if not user_row:
        return redirect(url_for('logout'))

    is_enabled = user_row['is_2fa_enabled']

    if is_enabled == 0:
        return redirect(url_for('setup_2fa'))

    if not session.get('is_2fa_verified'):
        return redirect(url_for('twofa_verification'))

    # Set user ID for detector
    if detector and hasattr(detector, 'set_user_id'):
        detector.set_user_id(user_id)

    conn = get_db_connection()
    if not conn:
        camera_url = 'error'
    else:
        try:
            c = conn.cursor()
            c.execute("SELECT camera_url_or_index FROM user_cameras WHERE user_id = ? AND is_active = 1 ORDER BY id LIMIT 1", 
                     (user_id,))
            camera = c.fetchone()
            camera_url = camera['camera_url_or_index'] if camera else '0'
        except sqlite3.Error as e:
            print(f"Error fetching default camera: {e}")
            camera_url = 'db_error'
        finally:
            conn.close()

    user_role = session.get('user_role', 'patient')
    success_msg = request.args.get('success')
    
    # Role-based dashboard routing
    if user_role == 'admin':
        return render_template("dashboard_admin.html",
                             user_name=user_name,
                             camera_url=camera_url,
                             is_2fa_set_up=(is_enabled == 1),
                             success=success_msg)
    elif user_role == 'doctor':
        return render_template("dashboard_doctor.html",
                             user_name=user_name,
                             camera_url=camera_url,
                             is_2fa_set_up=(is_enabled == 1),
                             success=success_msg)
    elif user_role == 'caretaker':
        return render_template("dashboard_caretaker.html",
                             user_name=user_name,
                             camera_url=camera_url,
                             is_2fa_set_up=(is_enabled == 1),
                             success=success_msg)
    else:  # patient
        return render_template("dashboard_patient.html",
                             user_name=user_name,
                             camera_url=camera_url,
                             is_2fa_set_up=(is_enabled == 1),
                             success=success_msg)

# =========================================================
# VIDEO FEED (NOW WITH PROPER FALL DETECTION)
# =========================================================
@app.route("/video_feed")
@login_required
@twofa_required
def video_feed():
    source = request.args.get('source', '0')
    if detector and hasattr(detector, 'set_camera_source'):
        detector.set_camera_source(source)
    from detection_skeleton import generate_frames_async
    return Response(generate_frames_async(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# =========================================================
# API ENDPOINTS
# =========================================================
@app.route("/api/falls")
@login_required
@twofa_required
def api_falls():
    """Return recent fall events (role-based filtering)"""
    user_id = session.get('user_id')
    user_role = session.get('user_role', 'patient')
    conn = get_db_connection()
    if not conn:
        return jsonify({"falls": []})

    try:
        c = conn.cursor()
        
        # Role-based query filtering
        if user_role == 'patient':
            # Patients see only their own falls
            query = """
            SELECT
                f.id, f.timestamp, f.status, f.details, u.name as user_name, f.user_id,
                f.video_path, f.severity, f.location
            FROM falls f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.user_id = ?
            ORDER BY f.timestamp DESC
            LIMIT 50
            """
            c.execute(query, (user_id,))
        elif user_role == 'caretaker':
            # Caretakers see falls from their assigned patients
            query = """
            SELECT
                f.id, f.timestamp, f.status, f.details, u.name as user_name, f.user_id,
                f.video_path, f.severity, f.location
            FROM falls f
            LEFT JOIN users u ON f.user_id = u.id
            INNER JOIN patient_caretaker pc ON f.user_id = pc.patient_id
            WHERE pc.caretaker_id = ? AND pc.is_active = 1
            ORDER BY f.timestamp DESC
            LIMIT 50
            """
            c.execute(query, (user_id,))
        else:  # doctor
            # Doctors see all falls
            query = """
            SELECT
                f.id, f.timestamp, f.status, f.details, u.name as user_name, f.user_id,
                f.video_path, f.severity, f.location
            FROM falls f
            LEFT JOIN users u ON f.user_id = u.id
            ORDER BY f.timestamp DESC
            LIMIT 50
            """
            c.execute(query)
        
        fall_rows = c.fetchall()

        falls_list = []
        for row in fall_rows:
            location = row['location'] if row['location'] else "Unknown Location"
            if location == "Unknown Location":
                try:
                    cam_cursor = conn.cursor()
                    cam_cursor.execute("SELECT location FROM user_cameras WHERE user_id = ? AND is_active = 1 LIMIT 1", 
                                     (row['user_id'],))
                    cam_loc = cam_cursor.fetchone()
                    if cam_loc: 
                        location = cam_loc['location']
                except: 
                    pass

            falls_list.append({
                "id": row['id'],
                "timestamp": row['timestamp'],
                "status": row['status'],
                "user_name": row['user_name'] or row['user_id'],
                "location": location,
                "details": row['details'],
                "video_path": row['video_path'] if 'video_path' in row.keys() and row['video_path'] else None,
                "severity": row['severity'] if 'severity' in row.keys() and row['severity'] else 'moderate',
                "has_video": bool(row['video_path'] if 'video_path' in row.keys() and row['video_path'] else None)
            })

        return jsonify({"falls": falls_list})
    except sqlite3.Error as e:
        print(f"Error fetching falls: {e}")
        return jsonify({"falls": []})
    finally:
        conn.close()

@app.route("/api/users")
@login_required
@twofa_required
def api_users():
    """Return users (role-based filtering)"""
    user_id = session.get('user_id')
    user_role = session.get('user_role', 'patient')
    conn = get_db_connection()
    if not conn:
        return jsonify({"users": []})

    try:
        c = conn.cursor()
        
        # Role-based query
        if user_role == 'patient':
            # Patients see only themselves
            query = """
            SELECT
                u.id, u.name, u.phone, u.email, u.role,
                MAX(f.timestamp) AS last_fall_time
            FROM users u
            LEFT JOIN falls f ON u.id = f.user_id AND f.status = 'CONFIRMED_FALL'
            WHERE u.id = ?
            GROUP BY u.id, u.name, u.phone, u.email, u.role
            """
            c.execute(query, (user_id,))
        elif user_role == 'caretaker':
            # Caretakers see their assigned patients
            query = """
            SELECT
                u.id, u.name, u.phone, u.email, u.role,
                MAX(f.timestamp) AS last_fall_time
            FROM users u
            INNER JOIN patient_caretaker pc ON u.id = pc.patient_id
            LEFT JOIN falls f ON u.id = f.user_id AND f.status = 'CONFIRMED_FALL'
            WHERE pc.caretaker_id = ? AND pc.is_active = 1
            GROUP BY u.id, u.name, u.phone, u.email, u.role
            ORDER BY u.name
            """
            c.execute(query, (user_id,))
        else:  # doctor
            # Doctors see all patients
            query = """
            SELECT
                u.id, u.name, u.phone, u.email, u.role,
                MAX(f.timestamp) AS last_fall_time
            FROM users u
            LEFT JOIN falls f ON u.id = f.user_id AND f.status = 'CONFIRMED_FALL'
            WHERE u.role = 'patient'
            GROUP BY u.id, u.name, u.phone, u.email, u.role
            ORDER BY u.name
            """
            c.execute(query)
        
        user_rows = c.fetchall()

        users_list = []
        for user in user_rows:
            status = "Active"
            last_fall = user['last_fall_time']
            if last_fall:
                try:
                    last_fall_dt = datetime.strptime(last_fall, "%Y-%m-%d %H:%M:%S")
                    if (datetime.utcnow() - last_fall_dt) < timedelta(hours=24):
                        status = "High Alert"
                except ValueError:
                    last_fall = 'Invalid Date Format'

            users_list.append({
                "id": user['id'],
                "name": user['name'],
                "phone": user['phone'] or 'N/A',
                "email": user['email'] or 'N/A',
                "role": user['role'] if 'role' in user.keys() and user['role'] else 'patient',
                "status": status,
                "last_fall": last_fall or 'None'
            })

        return jsonify({"users": users_list})
    except sqlite3.Error as e:
        print(f"Error fetching users: {e}")
        return jsonify({"users": []})
    finally:
        conn.close()

@app.route("/api/user/cameras", methods=["GET", "POST", "DELETE"])
@login_required
@twofa_required
def api_cameras():
    """API for managing user cameras"""
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        c = conn.cursor()

        if request.method == 'GET':
            c.execute(
                "SELECT * FROM user_cameras WHERE user_id = ? AND is_active = 1 ORDER BY created_at",
                (user_id,)
            )
            cameras = c.fetchall()
            cameras_list = [dict(cam) for cam in cameras]
            return jsonify({"cameras": cameras_list})

        elif request.method == 'POST':
            data = request.json
            name = data.get('camera_name')
            url = data.get('camera_url_or_index')
            loc = data.get('location', '')

            if not name or not url:
                return jsonify({'error': 'Missing camera name or URL/Index'}), 400

            c.execute(
                "INSERT INTO user_cameras (user_id, camera_name, camera_url_or_index, location) VALUES (?, ?, ?, ?)",
                (user_id, name, url, loc)
            )
            conn.commit()
            new_cam_id = c.lastrowid

            c.execute("SELECT COUNT(*) FROM user_cameras WHERE user_id = ? AND is_active = 1", (user_id,))
            if c.fetchone()[0] == 1 and detector and hasattr(detector, 'set_camera_source'):
                detector.set_camera_source(url)

            return jsonify({'message': 'Camera added successfully', 'id': new_cam_id, 'name': name}), 201

        elif request.method == 'DELETE':
            data = request.json
            cam_id = data.get('id')
            if not cam_id:
                return jsonify({'error': 'Missing camera ID'}), 400

            c.execute("SELECT camera_url_or_index FROM user_cameras WHERE id = ? AND user_id = ?", (cam_id, user_id))
            deleted_cam = c.fetchone()
            deleted_url = deleted_cam['camera_url_or_index'] if deleted_cam else None

            c.execute("UPDATE user_cameras SET is_active = 0 WHERE id = ? AND user_id = ?", (cam_id, user_id))
            conn.commit()

            if deleted_url and detector and detector.camera_source == deleted_url:
                c.execute("SELECT camera_url_or_index FROM user_cameras WHERE user_id = ? AND is_active = 1 ORDER BY id LIMIT 1", 
                         (user_id,))
                next_cam = c.fetchone()
                next_source = next_cam['camera_url_or_index'] if next_cam else '0'
                if hasattr(detector, 'set_camera_source'):
                    detector.set_camera_source(next_source)

            return jsonify({'message': 'Camera deleted successfully', 'id': cam_id}), 200

    except sqlite3.Error as e:
        print(f"Database error in /api/user/cameras: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        conn.close()

@app.route("/api/performance/metrics")
@login_required
@twofa_required
def api_performance_metrics():
    """Get current performance metrics"""
    try:
        metrics = detector.performance_monitor.calculate_comprehensive_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/performance/report")
@login_required
@twofa_required
def api_performance_report():
    """Generate detailed performance report"""
    try:
        report = detector.performance_monitor.generate_detailed_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/performance/save-report")
@login_required
@twofa_required
def api_save_performance_report():
    """Save performance report to file"""
    try:
        filename = detector.performance_monitor.save_report_to_file()
        return jsonify({"message": f"Report saved as {filename}", "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/performance/reset")
@login_required
@twofa_required
def api_reset_performance_metrics():
    """Reset performance metrics"""
    try:
        detector.performance_monitor.reset_metrics()
        return jsonify({"message": "Performance metrics reset successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sensitivity", methods=['GET', 'POST'])
@login_required
@twofa_required
def api_sensitivity():
    """API for getting/setting detection sensitivity"""
    current_threshold = detection_skeleton.FALL_THRESHOLD_VELOCITY

    if request.method == 'POST':
        data = request.json
        sensitivity_value = data.get('sensitivity')

        if sensitivity_value is not None:
            try:
                min_thresh = 0.005
                max_thresh = 0.05
                slider_val_norm = (float(sensitivity_value) - 0.1) / (1.0 - 0.1)
                new_threshold = max_thresh - (slider_val_norm * (max_thresh - min_thresh))

                detection_skeleton.FALL_THRESHOLD_VELOCITY = new_threshold
                # Also update the detector instance
                if detector:
                    detector.fall_indicators['velocity_threshold'] = new_threshold
                
                print(f"🎯 Fall threshold updated to: {new_threshold:.4f} (slider: {sensitivity_value})")
                return jsonify({"message": f"Sensitivity updated (threshold: {new_threshold:.4f})"}), 200
            except ValueError:
                return jsonify({"error": "Invalid sensitivity value"}), 400
        return jsonify({"error": "Missing sensitivity parameter"}), 400

    return jsonify({"sensitivity": current_threshold})

@app.route("/api/falls/<int:fall_id>/video")
@login_required
@twofa_required
def api_fall_video(fall_id):
    """Serve video file for a fall event"""
    from flask import send_from_directory
    import os
    
    user_id = session.get('user_id')
    user_role = session.get('user_role', 'patient')
    conn = get_db_connection()
    
    if not conn:
        return jsonify({"error": "Database error"}), 500
    
    try:
        c = conn.cursor()
        # Check access permissions
        if user_role == 'patient':
            c.execute("SELECT video_path, user_id FROM falls WHERE id = ? AND user_id = ?", 
                     (fall_id, user_id))
        elif user_role == 'caretaker':
            c.execute("""SELECT f.video_path, f.user_id FROM falls f
                        INNER JOIN patient_caretaker pc ON f.user_id = pc.patient_id
                        WHERE f.id = ? AND pc.caretaker_id = ? AND pc.is_active = 1""",
                     (fall_id, user_id))
        else:  # doctor
            c.execute("SELECT video_path, user_id FROM falls WHERE id = ?", (fall_id,))
        
        result = c.fetchone()
        if not result:
            return jsonify({"error": "Fall event not found or access denied"}), 404
        
        video_path = result['video_path']
        if not video_path or not os.path.exists(video_path):
            return jsonify({"error": "Video file not found"}), 404
        
        # Return video file
        video_dir = os.path.dirname(video_path)
        video_filename = os.path.basename(video_path)
        return send_from_directory(video_dir, video_filename, mimetype='video/mp4')
        
    except Exception as e:
        print(f"Error serving video: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/patients/assign", methods=['POST'])
@login_required
@twofa_required
def api_assign_patient():
    """Assign patient to doctor or caretaker"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    data = request.json
    
    patient_id = data.get('patient_id')
    relationship_type = data.get('type', 'caretaker')  # 'caretaker' or 'doctor'
    
    if user_role not in ['doctor', 'caretaker']:
        return jsonify({"error": "Only doctors and caretakers can assign patients"}), 403
    
    if not patient_id:
        return jsonify({"error": "Patient ID required"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500
    
    try:
        c = conn.cursor()
        
        # Verify patient exists
        c.execute("SELECT id FROM users WHERE id = ? AND role = 'patient'", (patient_id,))
        if not c.fetchone():
            return jsonify({"error": "Patient not found"}), 404
        
        if relationship_type == 'caretaker' and user_role == 'caretaker':
            # Assign patient to caretaker
            c.execute("""INSERT OR IGNORE INTO patient_caretaker 
                        (patient_id, caretaker_id, assigned_by) 
                        VALUES (?, ?, ?)""",
                     (patient_id, user_id, user_id))
            conn.commit()
            return jsonify({"message": "Patient assigned to caretaker successfully"}), 200
        elif relationship_type == 'doctor' and user_role == 'doctor':
            # Assign patient to doctor
            c.execute("""INSERT OR IGNORE INTO patient_doctor 
                        (patient_id, doctor_id) 
                        VALUES (?, ?)""",
                     (patient_id, user_id))
            conn.commit()
            return jsonify({"message": "Patient assigned to doctor successfully"}), 200
        else:
            return jsonify({"error": "Invalid assignment type for your role"}), 400
            
    except sqlite3.Error as e:
        print(f"Error assigning patient: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

# (Debug routes removed for production)

@app.route("/performance-dashboard")
@login_required
@twofa_required
def performance_dashboard():
    """Performance monitoring dashboard"""
    return render_template("performance_dashboard.html")

# =========================================================
# FEATURE LOG EXPORT
# =========================================================
@app.route('/api/features/export')
@login_required
@twofa_required
def export_feature_logs():
    try:
        from detection_skeleton import FEATURE_LOG_PATH
        import os
        if not os.path.exists(FEATURE_LOG_PATH):
            return jsonify({"error": "No feature log found"}), 404
        directory = os.path.dirname(FEATURE_LOG_PATH) or '.'
        filename = os.path.basename(FEATURE_LOG_PATH)
        return send_from_directory(directory=directory, path=filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# ALERT MANAGEMENT API
# =========================================================
@app.route('/api/alerts/status')
@login_required
@twofa_required
def api_alert_status():
    """Get alert service status and configuration"""
    try:
        from alert_service import alert_service
        return jsonify({
            'mode': alert_service.mode,
            'twilio_configured': alert_service.twilio_client is not None,
            'rules': {
                'severe': {'sms': True, 'call': True},
                'moderate': {'sms': True, 'call': False},
                'mild': {'sms': True, 'call': False}
            }
        })
    except ImportError:
        return jsonify({'mode': 'unavailable', 'error': 'Alert service not installed'}), 503

@app.route('/api/alerts/test', methods=['POST'])
@login_required
@twofa_required
def api_test_alert():
    """Send a test alert (for testing purposes)"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    if user_role not in ['doctor', 'caretaker']:
        return jsonify({"error": "Only doctors and caretakers can test alerts"}), 403
    
    try:
        from alert_service import send_fall_alerts, alert_service
        data = request.json
        severity = data.get('severity', 'moderate')
        
        # Get current user's name
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database error"}), 500
        
        try:
            c = conn.cursor()
            c.execute("SELECT name FROM users WHERE id = ?", (user_id,))
            user_row = c.fetchone()
            user_name = user_row[0] if user_row else "Test User"
            
            result = send_fall_alerts(
                patient_id=user_id,
                patient_name=user_name,
                severity=severity,
                location="Test Location",
                fall_id=None
            )
            
            return jsonify({
                "message": "Test alert sent",
                "mode": "mock" if alert_service.mode == 'mock' else "production",
                "result": result
            }), 200
        finally:
            conn.close()
    except ImportError:
        return jsonify({"error": "Alert service not available"}), 503

@app.route('/api/alerts/logs')
@login_required
@twofa_required
def api_alert_logs():
    """Get alert logs for current user's patients"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    conn = get_db_connection()
    
    if not conn:
        return jsonify({"logs": []})
    
    try:
        c = conn.cursor()
        
        # Role-based query
        if user_role == 'patient':
            query = """
                SELECT al.*, f.timestamp as fall_timestamp, f.severity
                FROM alert_logs al
                INNER JOIN falls f ON al.fall_id = f.id
                WHERE f.user_id = ?
                ORDER BY al.timestamp DESC
                LIMIT 50
            """
            c.execute(query, (user_id,))
        elif user_role == 'caretaker':
            query = """
                SELECT al.*, f.timestamp as fall_timestamp, f.severity
                FROM alert_logs al
                INNER JOIN falls f ON al.fall_id = f.id
                INNER JOIN patient_caretaker pc ON f.user_id = pc.patient_id
                WHERE pc.caretaker_id = ? AND pc.is_active = 1
                ORDER BY al.timestamp DESC
                LIMIT 50
            """
            c.execute(query, (user_id,))
        else:  # doctor
            query = """
                SELECT al.*, f.timestamp as fall_timestamp, f.severity
                FROM alert_logs al
                INNER JOIN falls f ON al.fall_id = f.id
                ORDER BY al.timestamp DESC
                LIMIT 100
            """
            c.execute(query)
        
        logs = []
        for row in c.fetchall():
            logs.append({
                'id': row['id'],
                'fall_id': row['fall_id'],
                'recipient_id': row['recipient_id'],
                'alert_type': row['alert_type'],
                'success': bool(row['success']),
                'details': row['details'],
                'timestamp': row['timestamp'],
                'fall_timestamp': row['fall_timestamp'] if 'fall_timestamp' in row.keys() and row['fall_timestamp'] else None,
                'severity': row['severity'] if 'severity' in row.keys() and row['severity'] else None
            })
        
        return jsonify({"logs": logs})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# =========================================================
# FALL REVIEW SYSTEM API
# =========================================================
@app.route('/api/falls/reviews')
@login_required
@twofa_required
def api_falls_reviews():
    """Get falls with review status for doctor dashboard"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    status_filter = request.args.get('status', 'all')
    severity_filter = request.args.get('severity', 'all')
    
    if user_role != 'doctor':
        return jsonify({"error": "Only doctors can access reviews"}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"falls": []})
    
    try:
        c = conn.cursor()
        
        # Build query
        query = """
            SELECT
                f.id, f.timestamp, f.status, f.details, f.severity, f.location,
                u.name as user_name, f.user_id, f.video_path,
                fr.id as review_id, fr.remarks, fr.recommendations, 
                fr.recommended_actions, fr.follow_up_date, fr.status as review_status
            FROM falls f
            LEFT JOIN users u ON f.user_id = u.id
            LEFT JOIN fall_reviews fr ON f.id = fr.fall_id AND fr.doctor_id = ?
            WHERE 1=1
        """
        params = [user_id]
        
        if severity_filter != 'all':
            query += " AND f.severity = ?"
            params.append(severity_filter)
        
        if status_filter == 'unreviewed':
            query += " AND fr.id IS NULL"
        elif status_filter != 'all':
            query += " AND fr.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY f.timestamp DESC LIMIT 50"
        
        c.execute(query, params)
        rows = c.fetchall()
        
        falls = []
        for row in rows:
            review = None
            if row['review_id']:
                import json
                review = {
                    'id': row['review_id'],
                    'remarks': row['remarks'],
                    'recommendations': row['recommendations'],
                    'recommended_actions': json.loads(row['recommended_actions']) if row['recommended_actions'] else [],
                    'follow_up_date': row['follow_up_date'],
                    'status': row['review_status']
                }
            
            falls.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'status': row['status'],
                'severity': row['severity'],
                'location': row['location'] or 'Unknown',
                'user_name': row['user_name'],
                'details': row['details'],
                'has_video': bool(row['video_path']),
                'review': review
            })
        
        return jsonify({"falls": falls})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"falls": []}), 500
    finally:
        conn.close()

@app.route('/api/falls/<int:fall_id>/review', methods=['GET', 'POST'])
@login_required
@twofa_required
def api_fall_review(fall_id):
    """Get or create/update fall review"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    if user_role != 'doctor':
        return jsonify({"error": "Only doctors can review falls"}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500
    
    try:
        c = conn.cursor()
        
        if request.method == 'GET':
            # Get fall and review
            c.execute("""
                SELECT f.*, u.name as user_name
                FROM falls f
                LEFT JOIN users u ON f.user_id = u.id
                WHERE f.id = ?
            """, (fall_id,))
            fall_row = c.fetchone()
            
            if not fall_row:
                return jsonify({"error": "Fall not found"}), 404
            
            c.execute("""
                SELECT * FROM fall_reviews
                WHERE fall_id = ? AND doctor_id = ?
            """, (fall_id, user_id))
            review_row = c.fetchone()
            
            review = None
            if review_row:
                import json
                review = {
                    'id': review_row['id'],
                    'remarks': review_row['remarks'],
                    'recommendations': review_row['recommendations'],
                    'recommended_actions': json.loads(review_row['recommended_actions']) if review_row['recommended_actions'] else [],
                    'follow_up_date': review_row['follow_up_date'],
                    'status': review_row['status']
                }
            
            fall = {
                'id': fall_row['id'],
                'timestamp': fall_row['timestamp'],
                'status': fall_row['status'],
                'severity': fall_row['severity'],
                'location': fall_row['location'],
                'user_name': fall_row['user_name'],
                'details': fall_row['details']
            }
            
            return jsonify({"fall": fall, "review": review})
        
        else:  # POST
            data = request.json
            import json
            
            # Check if review exists
            c.execute("SELECT id FROM fall_reviews WHERE fall_id = ? AND doctor_id = ?", (fall_id, user_id))
            existing = c.fetchone()
            
            recommended_actions_json = json.dumps(data.get('recommended_actions', []))
            recommendations_text = f"Recommended: {', '.join(data.get('recommended_actions', []))}"
            
            if existing:
                # Update
                c.execute("""
                    UPDATE fall_reviews
                    SET remarks = ?, recommendations = ?, recommended_actions = ?,
                        follow_up_date = ?, status = ?, updated_at = ?
                    WHERE id = ?
                """, (data.get('remarks'), recommendations_text, recommended_actions_json,
                      data.get('follow_up_date'), data.get('status', 'reviewed'),
                      datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), existing['id']))
            else:
                # Create
                c.execute("""
                    INSERT INTO fall_reviews (fall_id, doctor_id, remarks, recommendations,
                                           recommended_actions, follow_up_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (fall_id, user_id, data.get('remarks'), recommendations_text,
                      recommended_actions_json, data.get('follow_up_date'),
                      data.get('status', 'reviewed')))
            
            conn.commit()
            return jsonify({"message": "Review saved successfully"}), 200
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/falls/<int:fall_id>/report')
@login_required
@twofa_required
def api_generate_report(fall_id):
    """Generate PDF report for a fall"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    if user_role != 'doctor':
        return jsonify({"error": "Only doctors can generate reports"}), 403
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        import json
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get fall and review
        c.execute("""
            SELECT f.*, u.name as user_name, u.email, u.phone,
                   fr.remarks, fr.recommendations, fr.recommended_actions, fr.follow_up_date
            FROM falls f
            LEFT JOIN users u ON f.user_id = u.id
            LEFT JOIN fall_reviews fr ON f.id = fr.fall_id AND fr.doctor_id = ?
            WHERE f.id = ?
        """, (user_id, fall_id))
        
        row = c.fetchone()
        if not row:
            return jsonify({"error": "Fall not found"}), 404
        
        # Generate PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, "Fall Incident Report")
        
        # Fall Details
        y = height - 100
        p.setFont("Helvetica", 12)
        p.drawString(50, y, f"Patient: {row['user_name']}")
        y -= 20
        p.drawString(50, y, f"Date: {row['timestamp']}")
        y -= 20
        p.drawString(50, y, f"Severity: {row['severity'].upper()}")
        y -= 20
        p.drawString(50, y, f"Location: {row['location'] or 'Unknown'}")
        y -= 30
        
        # Review Details
        if row['remarks']:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y, "Doctor's Remarks:")
            y -= 20
            p.setFont("Helvetica", 10)
            remarks = row['remarks']
            for line in remarks.split('\n'):
                if y < 100:
                    p.showPage()
                    y = height - 50
                p.drawString(50, y, line[:80])
                y -= 15
        
        if row['recommendations']:
            y -= 10
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y, "Recommendations:")
            y -= 20
            p.setFont("Helvetica", 10)
            p.drawString(50, y, row['recommendations'])
            y -= 20
        
        if row['follow_up_date']:
            p.drawString(50, y, f"Follow-up Date: {row['follow_up_date']}")
        
        p.save()
        buffer.seek(0)
        
        return Response(buffer.getvalue(), mimetype='application/pdf',
                       headers={'Content-Disposition': f'attachment; filename=fall_report_{fall_id}.pdf'})
        
    except ImportError:
        # Fallback if reportlab not installed
        return jsonify({"error": "PDF generation requires reportlab. Install with: pip install reportlab"}), 503
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/falls/<int:fall_id>/files', methods=['GET', 'POST'])
@login_required
@twofa_required
def api_fall_files(fall_id):
    """Get or upload files for a fall"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500
    
    try:
        if request.method == 'GET':
            # Get files
            c = conn.cursor()
            c.execute("""
                SELECT ff.*, u.name as uploaded_by_name,
                       (SELECT COUNT(*) FROM file_comments WHERE file_id = ff.id) as comment_count
                FROM fall_files ff
                LEFT JOIN users u ON ff.uploaded_by = u.id
                WHERE ff.fall_id = ?
                ORDER BY ff.uploaded_at DESC
            """, (fall_id,))
            
            files = []
            for row in c.fetchall():
                files.append({
                    'id': row['id'],
                    'file_name': row['file_name'],
                    'file_type': row['file_type'],
                    'uploaded_by': row['uploaded_by_name'],
                    'uploaded_at': row['uploaded_at'],
                    'comment_count': row['comment_count']
                })
            
            return jsonify({"files": files})
        
        else:  # POST - Upload file
            if 'file' not in request.files:
                return jsonify({"error": "No file provided"}), 400
            
            file = request.files['file']
            file_type = request.form.get('file_type', 'other')
            
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            # Save file
            import os
            upload_dir = 'uploads'
            os.makedirs(upload_dir, exist_ok=True)
            
            filename = f"{fall_id}_{int(time.time())}_{file.filename}"
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            
            # Save to database
            c = conn.cursor()
            c.execute("""
                INSERT INTO fall_files (fall_id, uploaded_by, file_name, file_path, file_type, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (fall_id, user_id, file.filename, filepath, file_type, os.path.getsize(filepath)))
            
            conn.commit()
            return jsonify({"message": "File uploaded successfully", "file_id": c.lastrowid}), 200
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/files/<int:file_id>/comments', methods=['GET', 'POST'])
@login_required
@twofa_required
def api_file_comments(file_id):
    """Get or add comments on uploaded files"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    if request.method == 'POST' and user_role != 'doctor':
        return jsonify({"error": "Only doctors can comment on files"}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500
    
    try:
        if request.method == 'GET':
            c = conn.cursor()
            c.execute("""
                SELECT fc.*, u.name as doctor_name
                FROM file_comments fc
                LEFT JOIN users u ON fc.doctor_id = u.id
                WHERE fc.file_id = ?
                ORDER BY fc.created_at DESC
            """, (file_id,))
            
            comments = []
            for row in c.fetchall():
                comments.append({
                    'id': row['id'],
                    'comment': row['comment'],
                    'doctor_name': row['doctor_name'],
                    'created_at': row['created_at']
                })
            
            return jsonify({"comments": comments})
        
        else:  # POST
            data = request.json
            c = conn.cursor()
            c.execute("""
                INSERT INTO file_comments (file_id, doctor_id, comment)
                VALUES (?, ?, ?)
            """, (file_id, user_id, data.get('comment')))
            
            conn.commit()
            return jsonify({"message": "Comment added successfully"}), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/falls/<int:fall_id>/remarks')
@login_required
@twofa_required
def api_fall_remarks(fall_id):
    """Get doctor remarks for patient/caretaker view"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500
    
    try:
        c = conn.cursor()
        
        # Verify access
        if user_role == 'patient':
            c.execute("SELECT user_id FROM falls WHERE id = ? AND user_id = ?", (fall_id, user_id))
            if not c.fetchone():
                return jsonify({"error": "Access denied"}), 403
        elif user_role == 'caretaker':
            c.execute("""
                SELECT f.id FROM falls f
                INNER JOIN patient_caretaker pc ON f.user_id = pc.patient_id
                WHERE f.id = ? AND pc.caretaker_id = ? AND pc.is_active = 1
            """, (fall_id, user_id))
            if not c.fetchone():
                return jsonify({"error": "Access denied"}), 403
        
        # Get review
        c.execute("""
            SELECT fr.*, u.name as doctor_name
            FROM fall_reviews fr
            LEFT JOIN users u ON fr.doctor_id = u.id
            WHERE fr.fall_id = ?
            ORDER BY fr.created_at DESC
            LIMIT 1
        """, (fall_id,))
        
        review_row = c.fetchone()
        if not review_row:
            return jsonify({"review": None, "files": []})
        
        import json
        review = {
            'remarks': review_row['remarks'],
            'recommendations': review_row['recommendations'],
            'recommended_actions': json.loads(review_row['recommended_actions']) if review_row['recommended_actions'] else [],
            'follow_up_date': review_row['follow_up_date'],
            'doctor_name': review_row['doctor_name'],
            'review_date': review_row['review_date']
        }
        
        # Get files
        c.execute("""
            SELECT ff.*, u.name as uploaded_by_name
            FROM fall_files ff
            LEFT JOIN users u ON ff.uploaded_by = u.id
            WHERE ff.fall_id = ?
            ORDER BY ff.uploaded_at DESC
        """, (fall_id,))
        
        files = []
        for row in c.fetchall():
            files.append({
                'id': row['id'],
                'file_name': row['file_name'],
                'file_type': row['file_type'],
                'uploaded_by': row['uploaded_by_name'],
                'uploaded_at': row['uploaded_at']
            })
        
        return jsonify({"review": review, "files": files})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/patients/select", methods=['POST'])
@login_required
@twofa_required
def api_patient_select():
    """Allow patients to select their caretakers and doctors"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    data = request.json
    
    if user_role != 'patient':
        return jsonify({"error": "Only patients can select caretakers and doctors"}), 403
    
    caretaker_id = data.get('caretaker_id')
    doctor_id = data.get('doctor_id')
    
    if not caretaker_id and not doctor_id:
        return jsonify({"error": "At least one of caretaker_id or doctor_id is required"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500
    
    try:
        c = conn.cursor()
        results = []
        
        # Assign caretaker if provided
        if caretaker_id:
            # Verify caretaker exists and is a caretaker
            c.execute("SELECT id FROM users WHERE id = ? AND role = 'caretaker'", (caretaker_id,))
            if not c.fetchone():
                return jsonify({"error": "Caretaker not found"}), 404
            
            c.execute("""INSERT OR REPLACE INTO patient_caretaker 
                        (patient_id, caretaker_id, is_active, assigned_at)
                        VALUES (?, ?, 1, datetime('now'))""",
                     (user_id, caretaker_id))
            results.append("Caretaker assigned successfully")
        
        # Assign doctor if provided
        if doctor_id:
            # Verify doctor exists and is a doctor
            c.execute("SELECT id FROM users WHERE id = ? AND role = 'doctor'", (doctor_id,))
            if not c.fetchone():
                return jsonify({"error": "Doctor not found"}), 404
            
            c.execute("""INSERT OR REPLACE INTO patient_doctor 
                        (patient_id, doctor_id, is_active)
                        VALUES (?, ?, 1)""",
                     (user_id, doctor_id))
            results.append("Doctor assigned successfully")
        
        conn.commit()
        return jsonify({"message": "; ".join(results)}), 200
            
    except sqlite3.Error as e:
        print(f"Error selecting caretaker/doctor: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@app.route("/api/available/caretakers")
@login_required
@twofa_required
def api_available_caretakers():
    """Get list of available caretakers for patient selection"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"caretakers": []})
    
    try:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, email, phone
            FROM users
            WHERE role = 'caretaker'
            ORDER BY name
        """)
        caretakers = [{"id": row['id'], "name": row['name'], "email": row['email'], "phone": row['phone']} 
                     for row in c.fetchall()]
        return jsonify({"caretakers": caretakers})
    except sqlite3.Error as e:
        return jsonify({"caretakers": []})
    finally:
        conn.close()

@app.route("/api/available/doctors")
@login_required
@twofa_required
def api_available_doctors():
    """Get list of available doctors for patient selection"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"doctors": []})
    
    try:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, email, phone
            FROM users
            WHERE role = 'doctor'
            ORDER BY name
        """)
        doctors = [{"id": row['id'], "name": row['name'], "email": row['email'], "phone": row['phone']} 
                  for row in c.fetchall()]
        return jsonify({"doctors": doctors})
    except sqlite3.Error as e:
        return jsonify({"doctors": []})
    finally:
        conn.close()

@app.route("/api/admin/users")
@login_required
@twofa_required
def api_admin_users():
    """Admin endpoint to view all users and their activity"""
    user_role = session.get('user_role')
    if user_role != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"users": []})
    
    try:
        c = conn.cursor()
        c.execute("""
            SELECT 
                u.id, u.name, u.email, u.phone, u.role, u.created_at,
                COUNT(DISTINCT f.id) as fall_count,
                MAX(f.timestamp) as last_fall,
                COUNT(DISTINCT pc.caretaker_id) as caretaker_count,
                COUNT(DISTINCT pd.doctor_id) as doctor_count
            FROM users u
            LEFT JOIN falls f ON u.id = f.user_id
            LEFT JOIN patient_caretaker pc ON u.id = pc.patient_id AND pc.is_active = 1
            LEFT JOIN patient_doctor pd ON u.id = pd.patient_id AND pd.is_active = 1
            GROUP BY u.id, u.name, u.email, u.phone, u.role, u.created_at
            ORDER BY u.created_at DESC
        """)
        
        users = []
        for row in c.fetchall():
            users.append({
                "id": row['id'],
                "name": row['name'],
                "email": row['email'] or 'N/A',
                "phone": row['phone'] or 'N/A',
                "role": row['role'],
                "created_at": row['created_at'],
                "fall_count": row['fall_count'] or 0,
                "last_fall": row['last_fall'] or 'Never',
                "caretaker_count": row['caretaker_count'] or 0,
                "doctor_count": row['doctor_count'] or 0
            })
        
        return jsonify({"users": users})
    except sqlite3.Error as e:
        print(f"Error fetching admin users: {e}")
        return jsonify({"users": []})
    finally:
        conn.close()

@app.route("/api/admin/logs")
@login_required
@twofa_required
def api_admin_logs():
    """Admin endpoint to view system logs"""
    user_role = session.get('user_role')
    if user_role != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    # Get recent falls, alerts, and system activity
    conn = get_db_connection()
    if not conn:
        return jsonify({"logs": []})
    
    try:
        c = conn.cursor()
        
        # Get recent falls
        c.execute("""
            SELECT f.id, f.timestamp, f.status, f.severity, u.name as user_name, f.location
            FROM falls f
            LEFT JOIN users u ON f.user_id = u.id
            ORDER BY f.timestamp DESC
            LIMIT 100
        """)
        falls = [{"type": "fall", "id": row['id'], "timestamp": row['timestamp'], 
                 "status": row['status'], "severity": row['severity'], 
                 "user": row['user_name'], "location": row['location']} 
                for row in c.fetchall()]
        
        # Get recent alerts
        c.execute("""
            SELECT al.id, al.timestamp, al.alert_type, al.success, al.details, u.name as recipient_name
            FROM alert_logs al
            LEFT JOIN users u ON al.recipient_id = u.id
            ORDER BY al.timestamp DESC
            LIMIT 100
        """)
        alerts = [{"type": "alert", "id": row['id'], "timestamp": row['timestamp'],
                  "alert_type": row['alert_type'], "success": bool(row['success']),
                  "details": row['details'], "recipient": row['recipient_name']}
                 for row in c.fetchall()]
        
        # Combine and sort by timestamp
        all_logs = falls + alerts
        all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({"logs": all_logs[:200]})  # Return top 200
    except sqlite3.Error as e:
        print(f"Error fetching admin logs: {e}")
        return jsonify({"logs": []})
    finally:
        conn.close()

# =========================================================
# RUN APPLICATION
# =========================================================
if __name__ == "__main__":
    print("✅ Flask application initialized and ready.")
    print("🎯 Fall detection is ENABLED with MediaPipe fixes applied!")
    print("📊 Performance metrics will be tracked in real-time.")
    print("\n⚠️  IMPORTANT NOTES:")
    print("   - MediaPipe timestamp issues have been fixed")
    print("   - Frame processing includes error recovery")
    print("   - Pose detection rate is now monitored")
    print("   - Remove /debug routes before production deployment!")
    
    app.run(host='0.0.0.0', port=5000, debug=False)