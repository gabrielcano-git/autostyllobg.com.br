import os
import re
import requests
from pathlib import Path

API_BASE = os.getenv('WP_API_BASE', 'https://gabrielcanowp-djfpn.wpcomstaging.com/wp-json/wp/v2')
ROOT_DIR = Path(__file__).parent.parent.absolute()
CARROS_DIR = Path(os.getenv('CARROS_DIR', str(ROOT_DIR / '_carros')))

def wp_get_all(path):
    url = f"{API_BASE}{path}"
    params = {'per_page': 100}
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return []
        return response.json()
    except:
        return []

def get_local_cars():
    cars = {}
    if not CARROS_DIR.exists():
        return cars
    
    for path in CARROS_DIR.glob('*.md'):
        try:
            content = path.read_text(encoding='utf-8')
            match = re.search(r'^wp_id:\s*(\d+)', content, re.MULTILINE)
            if match:
                wp_id = int(match.group(1))
                cars[wp_id] = path.name
            else:
                cars[str(path)] = path.name
        except Exception as e:
            print(f"Erro ao ler {path.name}: {str(e)}")
    return cars

def compare():
    print("Buscando carros no WordPress...")
    wp_cars = wp_get_all('/carro')
    wp_ids = {c['id'] for c in wp_cars}
    wp_map = {c['id']: c['slug'] for c in wp_cars}

    print("Lendo carros locais em _carros/...")
    local_cars = get_local_cars()
    local_wp_ids = {k for k in local_cars.keys() if isinstance(k, int)}

    print("\n" + "="*40)
    print(" COMPARATIVO: CARROS ".center(40, "="))
    print("="*40 + "\n")

    # No WordPress mas não locais
    missing_locally = wp_ids - local_wp_ids
    if not missing_locally:
        print("✅ Todos os carros do WordPress estão presentes localmente (com wp_id).")
    else:
        print(f"❌ No WordPress mas NÃO localmente ({len(missing_locally)}):")
        for wid in sorted(missing_locally):
            print(f"   - ID: {wid} | Slug: {wp_map[wid]}")

    # Locais mas não no WordPress
    only_locally = []
    for key, filename in local_cars.items():
        if isinstance(key, int):
            if key not in wp_ids:
                only_locally.append(f"{filename} (wp_id: {key})")
        else:
            only_locally.append(f"{filename} (sem wp_id)")

    if not only_locally:
        print("\n✅ Não há carros locais extras.")
    else:
        print(f"\n❌ Locais mas NÃO no WordPress ({len(only_locally)}):")
        for info in sorted(only_locally):
            print(f"   - {info}")
    
    print("\n" + "="*40)
    
    # Banners
    print("\nBuscando banners no WordPress...")
    wp_banners = wp_get_all('/banner')
    wp_b_ids = {b['id'] for b in wp_banners}
    wp_b_map = {b['id']: b['slug'] for b in wp_banners}
    
    print("Lendo banners locais em _banners/...")
    BANNERS_DIR = ROOT_DIR / '_banners'
    local_banners = {}
    if BANNERS_DIR.exists():
        for path in BANNERS_DIR.glob('*.md'):
            content = path.read_text(encoding='utf-8')
            match = re.search(r'^wp_id:\s*(\d+)', content, re.MULTILINE)
            if match:
                local_banners[int(match.group(1))] = path.name
            else:
                local_banners[str(path)] = path.name
                
    local_b_ids = {k for k in local_banners.keys() if isinstance(k, int)}
    
    print("\n" + "="*40)
    print(" COMPARATIVO: BANNERS ".center(40, "="))
    print("="*40 + "\n")
    
    missing_b_locally = wp_b_ids - local_b_ids
    if not missing_b_locally:
        print("✅ Todos os banners do WordPress estão presentes localmente.")
    else:
        print(f"❌ No WordPress mas NÃO localmente ({len(missing_b_locally)}):")
        for wid in sorted(missing_b_locally):
            print(f"   - ID: {wid} | Slug: {wp_b_map[wid]}")
            
    only_b_locally = []
    for key, filename in local_banners.items():
        if isinstance(key, int):
            if key not in wp_b_ids:
                only_b_locally.append(f"{filename} (wp_id: {key})")
        else:
            only_b_locally.append(f"{filename} (sem wp_id)")
            
    if not only_b_locally:
        print("\n✅ Não há banners locais extras.")
    else:
        print(f"\n❌ Locais mas NÃO no WordPress ({len(only_b_locally)}):")
        for info in sorted(only_b_locally):
            print(f"   - {info}")
    print("\n" + "="*40)

if __name__ == "__main__":
    compare()
