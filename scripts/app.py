import os
import time
import shutil
import subprocess
from flask import Flask, request, jsonify
from importar import run_import

app = Flask(__name__)

# Segurança básica: você pode definir uma API_KEY no Cloud Run
API_KEY = os.getenv('IMPORT_API_KEY')

@app.before_request
def check_api_key():
    if API_KEY and request.headers.get('X-API-KEY') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

@app.route('/')
def health():
    return "Serviço de Importação Auto Styllo BG (Python) está rodando. Use POST /import para iniciar."

@app.route('/import', methods=['POST'])
def handle_import():
    repo_url = os.getenv('GIT_REPO_URL')
    github_token = os.getenv('GITHUB_TOKEN')
    branch = os.getenv('GIT_BRANCH', 'main')
    
    if not repo_url or not github_token:
        return jsonify({'error': 'GIT_REPO_URL e GITHUB_TOKEN são obrigatórios.'}), 500

    # Adiciona o token na URL do repositório para autenticação
    auth_repo_url = repo_url.replace('https://', f'https://x-access-token:{github_token}@')
    
    work_dir = f"/tmp/repo_{int(time.time())}"
    os.makedirs(work_dir, exist_ok=True)

    try:
        print(f"Clonando repositório branch {branch}...")
        subprocess.run(['git', 'clone', '--depth', '1', '--branch', branch, auth_repo_url, work_dir], check=True)
        
        # Mudar para o diretório de trabalho
        old_dir = os.getcwd()
        os.chdir(work_dir)
        
        try:
            # Configurar git
            subprocess.run(['git', 'config', 'user.name', 'Cloud Run Importer'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'importer@cloudrun.local'], check=True)

            # Rodar a importação sobrescrevendo as pastas locais no clone
            os.environ['CARROS_DIR'] = os.path.join(work_dir, '_carros')
            os.environ['BANNERS_DIR'] = os.path.join(work_dir, '_banners')
            
            results = run_import()
            
            # Verificar se houve mudanças
            status = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
            if not status.strip():
                return jsonify({'message': 'Sem mudanças detectadas.', 'results': results})

            # Commit e Push
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', 'chore: atualização automática de carros e banners via WordPress'], check=True)
            subprocess.run(['git', 'push', 'origin', branch], check=True)

            return jsonify({'message': 'Importação concluída e enviada ao Git!', 'results': results})
        
        finally:
            os.chdir(old_dir)
            
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Erro no comando git: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
