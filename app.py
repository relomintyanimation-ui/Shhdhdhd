# app.py - Main Flask Application for Hugging Face Spaces
import os
import time
import threading
import json
import uuid
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import firebase_admin
from firebase_admin import credentials, auth, db, firestore
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pyautogui
import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_TYPE'] = 'filesystem'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Firebase Configuration
firebase_config = {
    "apiKey": "AIzaSyCTqK0Qs8ELggN90WmUNwN3yPCWCEkkghk",
    "authDomain": "ff-bots.firebaseapp.com",
    "projectId": "ff-bots",
    "storageBucket": "ff-bots.firebasestorage.app",
    "messagingSenderId": "5910695918",
    "appId": "1:5910695918:web:d2496be78ebb6e9fcb48ff",
    "measurementId": "G-V3MGTFN6N7",
    "databaseURL": "https://ff-bots-default-rtdb.firebaseio.com/"
}

# Initialize Firebase with service account
try:
    # Try to load from file first
    if os.path.exists('firebase-credentials.json'):
        cred = credentials.Certificate('firebase-credentials.json')
    else:
        # Use environment variables for Hugging Face
        cred_dict = {
            "type": os.environ.get("FIREBASE_TYPE", "service_account"),
            "project_id": os.environ.get("FIREBASE_PROJECT_ID", "ff-bots"),
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL", ""),
            "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        cred = credentials.Certificate(cred_dict)
    
    firebase_admin.initialize_app(cred, firebase_config)
    db_firestore = firestore.client()
    logger.info("Firebase initialized successfully")
except Exception as e:
    logger.error(f"Firebase initialization error: {str(e)}")
    # Initialize without credentials for demo mode
    firebase_admin.initialize_app(options=firebase_config)
    db_firestore = None

# Global variables
active_bots = {}
bot_threads = {}
guest_accounts = {}
match_history = []
users = {
    "admin@example.com": {
        "password": "admin123",
        "name": "Admin User"
    }
}

class FreeFireBot:
    def __init__(self, email, password, bot_id):
        self.email = email
        self.password = password
        self.bot_id = bot_id
        self.driver = None
        self.status = "Stopped"
        self.current_match = 0
        self.team_code = None
        self.is_ready = False
        self.in_group = False
        self.screen_html = ""
        
    def setup_driver(self):
        """Setup Chrome driver for Hugging Face"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Run in headless mode for Hugging Face
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=400,800")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        # Mobile emulation
        mobile_emulation = {
            "deviceMetrics": {"width": 400, "height": 800, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36"
        }
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        try:
            # Try to use ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            # Fallback to default
            self.driver = webdriver.Chrome(options=chrome_options)
        
        return self.driver
    
    def get_screen_html(self):
        """Get current screen HTML for display"""
        if self.driver:
            try:
                return f"""
                <html>
                    <body style='background:#000; color:#0f0; font-family:monospace; padding:10px;'>
                        <h3>Bot: {self.email}</h3>
                        <p>Status: {self.status}</p>
                        <p>Match: {self.current_match}</p>
                        <p>Team Code: {self.team_code or 'None'}</p>
                        <p>URL: {self.driver.current_url}</p>
                        <hr>
                        <pre>{self.driver.page_source[:500]}...</pre>
                    </body>
                </html>
                """
            except:
                pass
        return f"""
        <html>
            <body style='background:#000; color:#0f0; font-family:monospace; padding:20px;'>
                <h2>🤖 Bot: {self.email}</h2>
                <p>Status: {self.status}</p>
                <p>Waiting for browser session...</p>
            </body>
        </html>
        """
    
    def login_freefire(self):
        """Simulate login to Free Fire"""
        try:
            if not self.driver:
                self.setup_driver()
            
            # Simulate login process
            self.driver.get("https://ff.garena.com/")
            time.sleep(2)
            
            # Try to find login elements (simplified for demo)
            try:
                login_btn = self.driver.find_element(By.XPATH, "//a[contains(text(),'Login')]")
                login_btn.click()
                time.sleep(1)
            except:
                pass
            
            self.status = "Logged In"
            socketio.emit('bot_status', {
                'account': self.email, 
                'status': 'Logged In',
                'match': self.current_match
            })
            return True
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            self.status = f"Error: {str(e)[:50]}"
            return False
    
    def join_guild(self, guild_code):
        """Join guild"""
        try:
            self.status = f"Joining Guild: {guild_code}"
            socketio.emit('bot_status', {'account': self.email, 'status': self.status})
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Guild join error: {str(e)}")
            return False
    
    def create_group(self):
        """Create a group/team"""
        try:
            self.team_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
            self.in_group = True
            self.status = f"Group Created: {self.team_code}"
            socketio.emit('bot_status', {'account': self.email, 'status': self.status})
            socketio.emit('team_code', {'code': self.team_code, 'creator': self.email})
            return self.team_code
        except Exception as e:
            logger.error(f"Create group error: {str(e)}")
            return None
    
    def join_group(self, team_code):
        """Join existing group"""
        try:
            self.team_code = team_code
            self.in_group = True
            self.status = f"Joined Group: {team_code}"
            socketio.emit('bot_status', {'account': self.email, 'status': self.status})
            return True
        except Exception as e:
            logger.error(f"Join group error: {str(e)}")
            return False
    
    def start_match(self):
        """Start match"""
        try:
            self.is_ready = True
            self.current_match += 1
            self.status = f"In Match #{self.current_match}"
            socketio.emit('bot_status', {
                'account': self.email, 
                'status': self.status,
                'match': self.current_match
            })
            return True
        except Exception as e:
            logger.error(f"Start match error: {str(e)}")
            return False
    
    def auto_play_loop(self, match_count=0):
        """Main auto-play loop"""
        matches_played = 0
        while match_count == 0 or matches_played < match_count:
            try:
                # Simulate match
                self.start_match()
                time.sleep(10)  # Simulate match time
                
                matches_played += 1
                self.status = f"Match Complete #{matches_played}"
                
                socketio.emit('match_complete', {
                    'account': self.email, 
                    'matches': matches_played
                })
                
                # Add to match history
                match_history.append({
                    'account': self.email,
                    'match': matches_played,
                    'time': time.strftime('%H:%M:%S'),
                    'status': 'Completed'
                })
                
                time.sleep(2)  # Brief pause between matches
                
            except Exception as e:
                logger.error(f"Auto play error: {str(e)}")
                time.sleep(5)
    
    def cleanup(self):
        """Cleanup driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

# Routes
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Simple authentication for demo
        if email in users and users[email]['password'] == password:
            session['user'] = email
            session['user_name'] = users[email]['name']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error="Passwords don't match")
        
        if email in users:
            return render_template('register.html', error="Email already exists")
        
        users[email] = {
            'password': password,
            'name': email.split('@')[0]
        }
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_guest', methods=['POST'])
def add_guest():
    data = request.json
    guest_id = data.get('guest_id')
    password = data.get('password')
    
    if len(guest_accounts) >= 4:
        return jsonify({'success': False, 'message': 'Maximum 4 accounts allowed'})
    
    guest_accounts[guest_id] = {
        'password': password,
        'status': 'Added',
        'bot_id': str(uuid.uuid4())[:8]
    }
    
    socketio.emit('guest_added', {'id': guest_id, 'status': 'Added'})
    
    return jsonify({'success': True, 'message': 'Guest account added'})

@app.route('/get_guests', methods=['GET'])
def get_guests():
    return jsonify(guest_accounts)

@app.route('/remove_guest', methods=['POST'])
def remove_guest():
    data = request.json
    guest_id = data.get('guest_id')
    
    if guest_id in guest_accounts:
        del guest_accounts[guest_id]
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Account not found'})

@app.route('/start_bots', methods=['POST'])
def start_bots():
    data = request.json
    selected_accounts = data.get('accounts', [])
    match_count = int(data.get('match_count', 0))
    guild_code = data.get('guild_code', '')
    
    # Clear previous bots
    for bot in active_bots.values():
        bot.cleanup()
    active_bots.clear()
    
    # Start new bots
    for acc in selected_accounts[:4]:
        if acc in guest_accounts:
            bot = FreeFireBot(acc, guest_accounts[acc]['password'], guest_accounts[acc]['bot_id'])
            active_bots[acc] = bot
            
            # Start bot in thread
            thread = threading.Thread(target=run_bot, args=(acc, bot, guild_code, match_count))
            thread.daemon = True
            thread.start()
            bot_threads[acc] = thread
    
    return jsonify({'success': True, 'message': f'Started {len(selected_accounts)} bots'})

def run_bot(account, bot, guild_code, match_count):
    """Run bot in thread"""
    try:
        # Setup and login
        bot.setup_driver()
        if bot.login_freefire():
            time.sleep(2)
            
            # Join guild if code provided
            if guild_code:
                bot.join_guild(guild_code)
                time.sleep(2)
            
            # Check if this is the first bot (group creator)
            accounts = list(active_bots.keys())
            if account == accounts[0] and len(accounts) > 1:
                team_code = bot.create_group()
                if team_code:
                    # Other bots join group
                    for other_acc in accounts[1:]:
                        if other_acc in active_bots:
                            time.sleep(2)
                            active_bots[other_acc].join_group(team_code)
            
            # Start auto play
            bot.auto_play_loop(match_count)
    
    except Exception as e:
        logger.error(f"Bot thread error: {str(e)}")
        socketio.emit('bot_error', {'account': account, 'error': str(e)})
    finally:
        bot.cleanup()

@app.route('/stop_bots', methods=['POST'])
def stop_bots():
    for account, bot in active_bots.items():
        bot.cleanup()
    
    active_bots.clear()
    bot_threads.clear()
    
    socketio.emit('bots_stopped', {'message': 'All bots stopped'})
    return jsonify({'success': True, 'message': 'All bots stopped'})

@app.route('/bot_status')
def bot_status():
    statuses = {}
    for acc, bot in active_bots.items():
        statuses[acc] = {
            'status': bot.status,
            'match': bot.current_match,
            'team_code': bot.team_code,
            'in_group': bot.in_group
        }
    return jsonify(statuses)

@app.route('/match_history')
def get_match_history():
    return jsonify(match_history[-50:])

@app.route('/bot_screen/<account>')
def bot_screen(account):
    if account in active_bots:
        return active_bots[account].get_screen_html()
    return "Bot not active", 404

# SocketIO events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connected', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

# Cleanup on exit
@atexit.register
def cleanup():
    for bot in active_bots.values():
        bot.cleanup()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))  # Hugging Face uses port 7860
    socketio.run(app, debug=False, host='0.0.0.0', port=port)