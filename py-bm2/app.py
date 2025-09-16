import json
import os
import sys
from flask import Flask, render_template

# Create a class to handle the sub-context/proxy fix
# This ensures that url_for() generates correct URLs when running in a sub-context
class ReverseProxied(object):
    def __init__(self, app, script_name=None):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        if self.script_name:
            environ['SCRIPT_NAME'] = self.script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(self.script_name):
                environ['PATH_INFO'] = path_info[len(self.script_name):]
        return self.app(environ, start_response)

app = Flask(__name__)

# Check for command-line argument for sub-context
prefix = ''
if len(sys.argv) > 1:
    prefix = sys.argv[1]
    # Add the proxy fix middleware
    app.wsgi_app = ReverseProxied(app.wsgi_app, script_name=prefix)

@app.route('/')
def index():
    """
    Reads bookmarks from the JSON file and renders the main page.
    """
    try:
        with open('bookmarks.json', 'r', encoding='utf-8') as f:
            bookmarks_data = json.load(f)
    except FileNotFoundError:
        bookmarks_data = {"Error": {"Message": {"bookmarks.json not found": "#"}}}
    
    return render_template('index.html', bookmarks=bookmarks_data)

if __name__ == '__main__':
    # Use port 5001 to avoid conflicts with other common dev servers
    app.run(debug=True, port=5001)