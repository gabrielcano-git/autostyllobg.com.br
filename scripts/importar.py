#!/usr/bin/env python3
import os
import re
import json
import yaml
import requests
import html
from urllib.parse import urlencode
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

# Configurações
API_BASE = os.getenv('WP_API_BASE', 'https://gabrielcanowp-djfpn.wpcomstaging.com/wp-json/wp/v2')
ROOT_DIR = Path(__file__).parent.parent.absolute()
CARROS_DIR = os.getenv('CARROS_DIR', str(ROOT_DIR / '_carros'))
BANNERS_DIR = os.getenv('BANNERS_DIR', str(ROOT_DIR / '_banners'))
WP_USER = os.getenv('WP_USER')
WP_APP_PASSWORD = os.getenv('WP_APP_PASSWORD')

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def wp_get(path, params=None):
    if params is None:
        params = {}
    
    url = f"{API_BASE}{path}"
    headers = {
        'User-Agent': 'Jekyll-Importer/1.0',
        'Accept': 'application/json'
    }
    auth = (WP_USER, WP_APP_PASSWORD) if WP_USER and WP_APP_PASSWORD else None
    response = requests.get(url, params=params, headers=headers, auth=auth)
    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code} para {url}")
    
    body = response.json()
    total_pages = int(response.headers.get('X-WP-TotalPages', 1))
    
    return body, total_pages

def wp_get_all(path, params=None):
    if params is None:
        params = {}
    
    page = 1
    all_items = []
    
    try:
        while True:
            params.update({'page': page, 'per_page': 100})
            items, total_pages = wp_get(path, params)
            
            if not isinstance(items, list) or not items:
                break
                
            all_items.extend(items)
            if page >= total_pages:
                break
            page += 1
    except Exception as e:
        print(f"  AVISO: falha ao buscar {path} — {str(e)}")
        
    return all_items

# ---------------------------------------------------------------------------
# Taxonomy / embed helpers
# ---------------------------------------------------------------------------

def extract_terms(embedded, taxonomy):
    term_groups = embedded.get('wp:term', [])
    flattened = [item for sublist in term_groups for item in sublist]
    
    results = []
    for t in flattened:
        if isinstance(t, dict) and t.get('taxonomy') == taxonomy:
            name = html.unescape(str(t.get('name', ''))).strip()
            if name:
                results.append(name)
    return results

def first_term(embedded, taxonomy):
    terms = extract_terms(embedded, taxonomy)
    return terms[0] if terms else None

def featured_url(embedded):
    media = embedded.get('wp:featuredmedia')
    if not isinstance(media, list) or not media:
        return None
    
    first = media[0]
    if not isinstance(first, dict):
        return None
        
    return first.get('source_url')

def fetch_gallery(post_id, featured, acf_image_ids=None):
    try:
        if acf_image_ids:
            ids_str = ','.join(str(i) for i in acf_image_ids)
            media_items, _ = wp_get('/media', params={'include': ids_str, 'per_page': 100})
            id_to_url = {m['id']: m['source_url'] for m in media_items if m.get('source_url')}
            urls = [id_to_url[i] for i in acf_image_ids if i in id_to_url]
        else:
            media_items, _ = wp_get('/media', params={'parent': post_id, 'per_page': 100})
            urls = list(dict.fromkeys(m['source_url'] for m in media_items if m.get('source_url')))

        if featured:
            if featured in urls:
                urls.remove(featured)
            urls.insert(0, featured)

        return urls
    except Exception as e:
        print(f"  AVISO: galeria do post {post_id} — {str(e)}")
        return [featured] if featured else []

# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def format_preco(value):
    if value is None:
        return None
    try:
        v = float(value)
        formatted = f"{v:,.2f}"  # "72,700.00" US format
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')  # "72.700,00"
    except (ValueError, TypeError):
        return value

def clean_wp_files(directory):
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    
    for path in dir_path.glob('*.md'):
        try:
            content = path.read_text(encoding='utf-8')
            if re.search(r'^wp_id:', content, re.MULTILINE):
                path.unlink()
                print(f"    Removido: {path.name}")
            else:
                print(f"    Mantido (sem wp_id): {path.name}")
        except Exception as e:
            print(f"    ERRO ao ler {path.name}: {str(e)}")

def render_frontmatter(data):
    # PyYAML by default might format strings differently. 
    # Jekyll standard is simple. Using safe_dump.
    
    # Custom representer for None values to show them as empty keys
    def represent_none(self, _):
        return self.represent_scalar('tag:yaml.org,2002:null', '')

    yaml.add_representer(type(None), represent_none, Dumper=yaml.SafeDumper)
    
    # We want top-level fields to be ordered or at least consistent.
    # Ruby script used a manual builder to ensure specific formatting.
    # Let's try to match it closely.
    
    content = "---\n"
    # Filter out empty body if present in data
    body = data.pop('body', None)
    
    # Re-order logic to match Ruby's behavior if needed, 
    # but regular YAML is usually fine for Jekyll.
    yaml_str = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    content += yaml_str
    content += "---\n"
    
    if body:
        content += f"\n{body.strip()}\n"
    
    return content

def write_md(filepath, frontmatter, body=None):
    data = frontmatter.copy()
    if body:
        data['body'] = body
    
    content = render_frontmatter(data)
    Path(filepath).write_text(content, encoding='utf-8')

# ---------------------------------------------------------------------------
# Import: Carros
# ---------------------------------------------------------------------------

def import_carros():
    print("\n==> Importando carros...")
    
    carros = wp_get_all('/carro', params={'_embed': 1})
    total = len(carros)
    imported = 0
    seen_slugs = set()
    
    print(f"    {total} carro(s) encontrado(s) na API")
    
    for idx, carro in enumerate(carros):
        try:
            raw_slug = str(carro.get('slug', '')).strip()
            if not raw_slug:
                raw_slug = f"carro-{carro['id']}"
            
            slug = raw_slug
            if slug in seen_slugs:
                slug = f"{raw_slug}-{carro['id']}"
                print(f"  AVISO: slug duplicado '{raw_slug}', renomeado para '{slug}'")
            seen_slugs.add(slug)
            
            embedded = carro.get('_embedded', {})
            acf = carro.get('acf') or {}
            if isinstance(acf, list):
                acf = {}

            marca = first_term(embedded, 'marca')
            modelo = first_term(embedded, 'modelo')
            cambio = first_term(embedded, 'cambio')
            combustivel = first_term(embedded, 'combustivel')
            cor = first_term(embedded, 'cor')
            opcionais = extract_terms(embedded, 'opcional')
            
            anos = sorted(extract_terms(embedded, 'ano'))
            ano_str = "/".join(anos) if anos else None
            
            # Título do WordPress (prioridade)
            raw_title = html.unescape(carro.get('title', {}).get('rendered', '')).strip()
            
            # Título composto (fallback se rendered estiver vazio)
            parts = [p for p in [marca, modelo, ano_str] if p]
            composed = " ".join(parts)
            title = raw_title if raw_title else (composed if composed else slug)
            
            featured = featured_url(embedded)
            imagens = fetch_gallery(carro['id'], featured, acf.get('imagens'))
            
            body = html.unescape(carro.get('content', {}).get('rendered', '')).strip()
            
            acf_opcionais = acf.get('itens_e_opcionais')
            if isinstance(acf_opcionais, str) and acf_opcionais.strip():
                acf_opcionais = [o.strip() for o in acf_opcionais.replace('\n', ',').split(',') if o.strip()]
            elif not isinstance(acf_opcionais, list):
                acf_opcionais = []

            frontmatter = {
                'wp_id': carro['id'],
                'title': title if title else slug,
                'marca': marca,
                'modelo': modelo,
                'ano': ano_str,
                'km': acf.get('quilometragem'),
                'preco': format_preco(acf.get('preco')),
                'cambio': cambio,
                'combustivel': combustivel,
                'cor': cor,
                'portas': None,
                'destaque': None,
                'opcionais': opcionais if opcionais else acf_opcionais,
                'imagens': imagens,
            }
            
            filepath = Path(CARROS_DIR) / f"{slug}.md"
            write_md(filepath, frontmatter, body)
            
            imported += 1
            print(f"  [{idx + 1}/{total}] {slug}")
        except Exception as e:
            print(f"  ERRO ao importar carro ID {carro.get('id')}: {str(e)}")
            
    return imported

# ---------------------------------------------------------------------------
# Import: Banners
# ---------------------------------------------------------------------------

def import_banners():
    print("\n==> Importando banners...")
    
    banners = wp_get_all('/banner', params={'_embed': 1})
    total = len(banners)
    imported = 0
    
    print(f"    {total} banner(s) encontrado(s) na API")
    
    for idx, banner in enumerate(banners):
        try:
            slug = str(banner.get('slug', '')).strip()
            if not slug:
                slug = f"banner-{banner['id']}"
                
            embedded = banner.get('_embedded', {})
            imagem = featured_url(embedded)
            title = html.unescape(banner.get('title', {}).get('rendered', '')).strip()
            
            frontmatter = {
                'wp_id': banner['id'],
                'title': title if title else slug,
                'imagem': imagem,
                'link': None,
                'cta': None,
                'subtitulo': None,
                'ativo': True,
                'ordem': idx + 1,
            }
            
            filepath = Path(BANNERS_DIR) / f"{slug}.md"
            write_md(filepath, frontmatter)
            
            imported += 1
            print(f"  [{idx + 1}/{total}] {slug}")
        except Exception as e:
            print(f"  ERRO ao importar banner ID {banner.get('id')}: {str(e)}")
            
    return imported

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_import():
    Path(CARROS_DIR).mkdir(parents=True, exist_ok=True)
    Path(BANNERS_DIR).mkdir(parents=True, exist_ok=True)
    
    print('==> Limpando arquivos gerados anteriormente...')
    print("    _carros/:")
    clean_wp_files(CARROS_DIR)
    print("    _banners/:")
    clean_wp_files(BANNERS_DIR)
    
    carros_importados = import_carros()
    banners_importados = import_banners()
    
    print("\n==> Concluído!")
    print(f"    Carros importados : {carros_importados}")
    print(f"    Banners importados: {banners_importados}")
    
    return {
        'carros': carros_importados,
        'banners': banners_importados
    }

if __name__ == "__main__":
    run_import()
    print("\nPróximo passo: bundle exec jekyll serve")
