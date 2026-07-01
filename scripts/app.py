import os
import subprocess
import shutil
import tempfile
import threading
from datetime import datetime, timezone
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
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY', 'gabrielcano-git/autostyllobg.com.br')
GIT_BRANCH = os.getenv('GIT_BRANCH', 'main')
WORK_BASE_DIR = Path(os.getenv('IMPORT_WORK_BASE_DIR', '/tmp/autostyllobg-importador'))

_lock = threading.Lock()
_status = {
    'running': False,
    'last_result': None,
    'last_error': None,
    'started_at': None,
    'finished_at': None,
}


def _check_auth(req):
    auth = req.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    return auth[len('Bearer '):] == IMPORT_TOKEN


def _now():
    return datetime.now(timezone.utc).isoformat()


def _redact(value):
    if GITHUB_TOKEN:
        value = value.replace(GITHUB_TOKEN, '[redacted]')
    return value


def _git(args, cwd):
    r = subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        output = r.stderr.strip() or r.stdout.strip()
        raise RuntimeError(_redact(output))
    return r.stdout.strip()


def _require_config():
    missing = []
    if not IMPORT_TOKEN:
        missing.append('IMPORT_TOKEN')
    if not GITHUB_TOKEN:
        missing.append('GITHUB_TOKEN')
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")


def _clone_workspace():
    WORK_BASE_DIR.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix='run-', dir=WORK_BASE_DIR))
    repo_url = f'https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git'

    try:
        _git([
            'clone',
            '--branch',
            GIT_BRANCH,
            '--single-branch',
            repo_url,
            str(workspace),
        ], cwd=WORK_BASE_DIR)
        return workspace
    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise


def _do_import():
    workspace = None

    try:
        _require_config()
        workspace = _clone_workspace()

        _git(['config', 'user.name', GIT_USER_NAME], cwd=workspace)
        _git(['config', 'user.email', GIT_USER_EMAIL], cwd=workspace)

        import_result = run_import(root_dir=workspace)

        _git(['add', '_carros/', '_banners/'], cwd=workspace)
        diff = _git(['status', '--porcelain'], cwd=workspace)

        result = {
            'success': True,
            'import': import_result,
            'pushed': False,
            'commit_sha': None,
            'message': 'Import completed; no changes to commit.',
        }

        if diff:
            _git(['commit', '-m', 'chore: atualiza conteúdo do WordPress'], cwd=workspace)
            _git(['push', 'origin', GIT_BRANCH], cwd=workspace)
            result.update({
                'pushed': True,
                'commit_sha': _git(['rev-parse', 'HEAD'], cwd=workspace),
                'message': 'Import completed and pushed.',
            })

        return result
    finally:
        if workspace:
            shutil.rmtree(workspace, ignore_errors=True)


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

    if not _lock.acquire(blocking=False):
        return jsonify({'status': 'already_running'}), 409

    _status['running'] = True
    _status['started_at'] = _now()
    _status['finished_at'] = None
    _status['last_result'] = None
    _status['last_error'] = None

    try:
        result = _do_import()
        _status['last_result'] = result
        return jsonify(result), 200
    except Exception as e:
        error = _redact(str(e))
        _status['last_error'] = error
        return jsonify({'success': False, 'error': error}), 500
    finally:
        _status['running'] = False
        _status['finished_at'] = _now()
        _lock.release()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
