from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from functools import wraps
import json
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this!

# Configuration
DATA_FILE = 'links_data.json'
API_PASSWORD = 'password'  # CHANGE THIS PASSWORD!

# HTML Template for the UI
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - URL Manager</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 16px;
        }
        button {
            width: 100%;
            background-color: #667eea;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }
        button:hover {
            background-color: #5568d3;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
            text-align: center;
        }
        .lock-icon {
            text-align: center;
            font-size: 48px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="lock-icon">🔒</div>
        <h1>URL Manager Login</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Password:</label>
                <input type="password" name="password" required autofocus>
            </div>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>URL Manager</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h1 { color: #333; margin: 0; }
        .logout-btn {
            background-color: #f44336;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .logout-btn:hover { background-color: #da190b; }
        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        button:hover { background-color: #45a049; }
        button.delete { background-color: #f44336; }
        button.delete:hover { background-color: #da190b; }
        .app-card {
            background: #f9f9f9;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }
        .url-item {
            background: white;
            padding: 10px;
            margin: 5px 0;
            border-radius: 3px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .url-label { font-weight: bold; color: #666; }
        .url-value { color: #333; flex-grow: 1; margin-left: 10px; }
        .message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        .link-inputs {
            background: #f0f0f0;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔗 URL Manager</h1>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>
    
    <div class="container">
        <h2>Add New Application</h2>
        <form id="addAppForm">
            <div class="form-group">
                <label>Application Key:</label>
                <input type="text" id="appKey" required>
            </div>
            <div id="linkInputs" class="link-inputs">
                <h3>Links:</h3>
                <div class="form-group">
                    <label>Link Name (e.g., regression_test_link):</label>
                    <input type="text" class="link-name" required>
                </div>
                <div class="form-group">
                    <label>Link URL:</label>
                    <input type="text" class="link-url" required>
                </div>
                <button type="button" onclick="addLinkField()">+ Add Another Link</button>
            </div>
            <br>
            <button type="submit">Save Application</button>
        </form>
    </div>

    <div class="container">
        <h2>Existing Applications</h2>
        <div id="appsList"></div>
    </div>

    <div class="container">
        <h2>API Usage</h2>
        <p><strong>Get links for an app:</strong></p>
        <code>GET /getlinks/&lt;app_key&gt;</code>
        <p style="margin-top: 10px;"><strong>Example:</strong></p>
        <code>http://localhost:5000/getlinks/my_app</code>
    </div>

    <script>
        function addLinkField() {
            const container = document.getElementById('linkInputs');
            const div = document.createElement('div');
            div.innerHTML = `
                <div class="form-group">
                    <label>Link Name:</label>
                    <input type="text" class="link-name" required>
                </div>
                <div class="form-group">
                    <label>Link URL:</label>
                    <input type="text" class="link-url" required>
                </div>
            `;
            container.appendChild(div);
        }

        document.getElementById('addAppForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const appKey = document.getElementById('appKey').value;
            const linkNames = document.querySelectorAll('.link-name');
            const linkUrls = document.querySelectorAll('.link-url');
            
            const links = {};
            for (let i = 0; i < linkNames.length; i++) {
                if (linkNames[i].value && linkUrls[i].value) {
                    links[linkNames[i].value] = linkUrls[i].value;
                }
            }
            
            const response = await fetch('/api/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({app_key: appKey, links: links})
            });
            
            const result = await response.json();
            alert(result.message);
            
            if (response.ok) {
                document.getElementById('addAppForm').reset();
                loadApps();
            }
        });

        async function loadApps() {
            const response = await fetch('/api/list');
            const data = await response.json();
            
            const appsList = document.getElementById('appsList');
            appsList.innerHTML = '';
            
            for (const [appKey, links] of Object.entries(data)) {
                const card = document.createElement('div');
                card.className = 'app-card';
                
                let linksHtml = '';
                for (const [name, url] of Object.entries(links)) {
                    linksHtml += `
                        <div class="url-item">
                            <span class="url-label">${name}:</span>
                            <span class="url-value">${url}</span>
                        </div>
                    `;
                }
                
                card.innerHTML = `
                    <h3>${appKey}</h3>
                    ${linksHtml}
                    <button class="delete" onclick="deleteApp('${appKey}')">Delete Application</button>
                `;
                appsList.appendChild(card);
            }
        }

        async function deleteApp(appKey) {
            if (!confirm(`Delete application "${appKey}"?`)) return;
            
            const response = await fetch(`/api/delete/${appKey}`, {method: 'DELETE'});
            const result = await response.json();
            alert(result.message);
            loadApps();
        }

        // Load apps on page load
        loadApps();
    </script>
</body>
</html>
"""

# Helper functions
def login_required(f):
    """Decorator to require login for UI routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_data():
    """Load data from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    """Save data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == API_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Invalid password")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# API Endpoints
@app.route('/getlinks/<app_key>', methods=['GET'])
def get_links(app_key):
    """Get all links for a specific app_key (no password required)"""
    data = load_data()
    
    if app_key in data:
        return jsonify(data[app_key]), 200
    else:
        return jsonify({"error": "Application key not found"}), 404

@app.route('/api/add', methods=['POST'])
@login_required
def add_app():
    """Add or update an application's links"""
    req_data = request.get_json()
    app_key = req_data.get('app_key')
    links = req_data.get('links', {})
    
    if not app_key:
        return jsonify({"error": "app_key is required"}), 400
    
    data = load_data()
    data[app_key] = links
    save_data(data)
    
    return jsonify({"message": f"Application '{app_key}' saved successfully"}), 200

@app.route('/api/list', methods=['GET'])
@login_required
def list_apps():
    """List all applications and their links"""
    return jsonify(load_data()), 200

@app.route('/api/delete/<app_key>', methods=['DELETE'])
@login_required
def delete_app(app_key):
    """Delete an application"""
    data = load_data()
    
    if app_key in data:
        del data[app_key]
        save_data(data)
        return jsonify({"message": f"Application '{app_key}' deleted"}), 200
    else:
        return jsonify({"error": "Application key not found"}), 404

@app.route('/', methods=['GET'])
@login_required
def index():
    """Render the UI"""
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    print("🚀 URL Manager API starting...")
    print(f"📁 Data will be stored in: {os.path.abspath(DATA_FILE)}")
    print(f"🔐 UI password protection enabled")
    print(f"⚠️  IMPORTANT: Change API_PASSWORD in the code!")
    print("🌐 UI (password protected): http://localhost:5000")
    print("📡 API (open access): http://localhost:5000/getlinks/<app_key>")
    app.run(debug=True, host='0.0.0.0', port=5000)