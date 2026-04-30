import os
import threading
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

from scripts.importar import run_import

app = Flask(__name__)

IMPORT_TOKEN = os.getenv('IMPORT_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GIT_USER_NAME = os.getenv('GIT_USER_NAME', 'Import Bot')
GIT_USER_EMAIL = os.getenv('GIT_USER_EMAIL', 'bot@autostyllobg.com.br')
REPO_DIR = str(Path(__file__).parent.parent)

_lock = threading.Lock()
_status = {'running': False, 'last_result': None, 'last_error': None}


def _check_auth(req):
    auth = req.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    return auth[len('Bearer '):] == IMPORT_TOKEN


def _git(args):
    r = subprocess.run(['git'] + args, cwd=REPO_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()


def _do_import():
    with _lock:
        _status['running'] = True
        _status['last_error'] = None
        _status['last_result'] = None
        try:
            if GITHUB_TOKEN:
                https_url = f'https://x-access-token:{GITHUB_TOKEN}@github.com/gabrielcano-git/autostyllobg.com.br.git'
                _git(['remote', 'set-url', 'origin', https_url])

            _git(['config', 'user.name', GIT_USER_NAME])
            _git(['config', 'user.email', GIT_USER_EMAIL])
            _git(['pull', '--rebase'])

            result = run_import()

            _git(['add', '_carros/', '_banners/'])

            diff = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=REPO_DIR, capture_output=True, text=True
            ).stdout.strip()

            if diff:
                _git(['commit', '-m', 'chore: atualiza conteúdo do WordPress'])
                _git(['push'])

            _status['last_result'] = result
        except Exception as e:
            _status['last_error'] = str(e)
        finally:
            _status['running'] = False


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


@app.route('/status', methods=['GET'])
def get_status():
    if not _check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(_status), 200


@app.route('/import', methods=['POST'])
def trigger_import():
    if not _check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    if _status['running']:
        return jsonify({'status': 'already_running'}), 409
    thread = threading.Thread(target=_do_import, daemon=True)
    thread.start()
    return jsonify({'status': 'accepted'}), 202


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
