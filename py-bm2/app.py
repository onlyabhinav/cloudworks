import json
import os
import sys
from flask import Flask, render_template

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

prefix = ''
if len(sys.argv) > 1:
    prefix = sys.argv[1]
    app.wsgi_app = ReverseProxied(app.wsgi_app, script_name=prefix)

ICON_MAP = {
    'github.com': 'fa-brands fa-github',
    'gitlab.com': 'fa-brands fa-gitlab',
    'bitbucket.org': 'fa-brands fa-bitbucket',
    'stackoverflow.com': 'fa-brands fa-stack-overflow',
    'python.org': 'fa-brands fa-python',
    'docker.com': 'fa-brands fa-docker',
    'kubernetes.io': 'fa-solid fa-dharmachakra',
    'aws.amazon.com': 'fa-brands fa-aws',
    'cloud.google.com': 'fa-solid fa-cloud',
    'developer.mozilla.org': 'fa-brands fa-firefox-browser',
    'jira': 'fa-brands fa-jira',
    'jenkins': 'fa-brands fa-jenkins',
    'postman.com': 'fa-solid fa-rocket',
    'figma.com': 'fa-brands fa-figma'
}
DEFAULT_ICON = 'fa-solid fa-link'

def get_icon_for_url(url):
    for keyword, icon_class in ICON_MAP.items():
        if keyword in url:
            return icon_class
    return DEFAULT_ICON

@app.context_processor
def inject_utilities():
    return dict(get_icon_for_url=get_icon_for_url)

@app.route('/')
def index():
    try:
        with open('bookmarks.json', 'r', encoding='utf-8') as f:
            bookmarks_data = json.load(f)
    except FileNotFoundError:
        bookmarks_data = {"Error": {"Message": {"bookmarks.json not found": "#"}}}
    
    return render_template('index.html', bookmarks=bookmarks_data)

if __name__ == '__main__':
    app.run(debug=True, port=5001)