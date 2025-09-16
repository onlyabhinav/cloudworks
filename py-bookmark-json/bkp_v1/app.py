from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

def load_bookmarks():
    """Load bookmarks from JSON file"""
    try:
        with open('bookmarks.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create sample data if file doesn't exist
        sample_data = {
            "common links": {
                "Development": {
                    "GitHub": "https://github.com",
                    "Stack Overflow": "https://stackoverflow.com",
                    "MDN Docs": "https://developer.mozilla.org"
                },
                "Tools": {
                    "VS Code": "https://code.visualstudio.com",
                    "Postman": "https://postman.com",
                    "Docker Hub": "https://hub.docker.com"
                }
            },
            "application-1 links": {
                "Database": {
                    "Admin Panel": "https://app1-admin.example.com",
                    "Monitoring": "https://app1-monitor.example.com"
                },
                "APIs": {
                    "User API": "https://app1-api.example.com/users",
                    "Payment API": "https://app1-api.example.com/payments"
                }
            },
            "application-2 links": {
                "Infrastructure": {
                    "AWS Console": "https://app2-aws.example.com",
                    "Kubernetes": "https://app2-k8s.example.com"
                },
                "Monitoring": {
                    "Grafana": "https://app2-grafana.example.com",
                    "Prometheus": "https://app2-prometheus.example.com"
                }
            }
        }
        with open('bookmarks.json', 'w') as f:
            json.dump(sample_data, f, indent=2)
        return sample_data

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/bookmarks')
def api_bookmarks():
    """API endpoint to get bookmarks data"""
    return jsonify(load_bookmarks())

if __name__ == '__main__':
    print("🚀 Starting Bookmark Application...")
    print("📁 Make sure your bookmarks.json file is in the same directory")
    print("🌐 Open http://localhost:5000 in your browser")
    print("📋 Click the copy button next to any link to copy it to clipboard")
    print("🔍 Use section filters to show/hide specific sections")
    app.run(debug=True, host='0.0.0.0', port=5000)