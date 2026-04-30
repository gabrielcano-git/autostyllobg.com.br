#!/usr/bin/env ruby
# scripts/importar.rb
# Importa conteúdo do WordPress REST API para as coleções Jekyll.
# Uso: ruby scripts/importar.rb
# Requer apenas stdlib Ruby (net/http, json, yaml, fileutils, cgi, set).

require 'net/http'
require 'net/https'
require 'json'
require 'yaml'
require 'fileutils'
require 'cgi'
require 'set'
require 'uri'

API_BASE    = ENV['WP_API_BASE'] || 'https://gabrielcanowp-djfpn.wpcomstaging.com/wp-json/wp/v2'
ROOT_DIR    = File.expand_path('..', __dir__)
CARROS_DIR  = ENV['CARROS_DIR']  || File.join(ROOT_DIR, '_carros')
BANNERS_DIR = ENV['BANNERS_DIR'] || File.join(ROOT_DIR, '_banners')

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def wp_get(path, params = {})
  uri = URI("#{API_BASE}#{path}")
  uri.query = URI.encode_www_form(params) unless params.empty?

  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = (uri.scheme == 'https')
  http.read_timeout = 30
  http.open_timeout = 10

  request = Net::HTTP::Get.new(uri)
  request['User-Agent'] = 'Jekyll-Importer/1.0'
  request['Accept']     = 'application/json'

  response = http.request(request)

  unless response.is_a?(Net::HTTPSuccess)
    raise "HTTP #{response.code} para #{uri}"
  end

  body        = JSON.parse(response.body)
  total_pages = response['X-WP-TotalPages']&.to_i || 1

  [body, total_pages]
end

def wp_get_all(path, params = {})
  page       = 1
  all_items  = []

  loop do
    items, total_pages = wp_get(path, params.merge(page: page, per_page: 100))

    # Quando não há itens o WP retorna [] (array vazio)
    break if items.is_a?(Array) && items.empty?

    all_items.concat(items)
    break if page >= total_pages

    page += 1
  end

  all_items
rescue => e
  warn "  AVISO: falha ao buscar #{path} — #{e.message}"
  []
end

# ---------------------------------------------------------------------------
# Taxonomy / embed helpers
# ---------------------------------------------------------------------------

def extract_terms(embedded, taxonomy)
  term_groups = embedded&.dig('wp:term') || []
  term_groups.flatten
             .select  { |t| t.is_a?(Hash) && t['taxonomy'] == taxonomy }
             .map     { |t| CGI.unescapeHTML(t['name'].to_s).strip }
             .reject  { |n| n.empty? }
end

def first_term(embedded, taxonomy)
  extract_terms(embedded, taxonomy).first
end

def featured_url(embedded)
  media = embedded&.dig('wp:featuredmedia')
  return nil unless media.is_a?(Array) && !media.empty?

  first = media.first
  return nil unless first.is_a?(Hash)

  first['source_url']
end

# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------

def fetch_gallery(post_id, featured)
  media_items, = wp_get('/media', parent: post_id, per_page: 100)
  urls = media_items.map { |m| m['source_url'] }.compact.uniq

  if featured
    urls.delete(featured)
    urls.unshift(featured)
  end

  urls
rescue => e
  warn "  AVISO: galeria do post #{post_id} — #{e.message}"
  featured ? [featured] : []
end

# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def clean_wp_files(dir)
  FileUtils.mkdir_p(dir)

  Dir.glob(File.join(dir, '*.md')).each do |path|
    content = File.read(path)
    if content =~ /^wp_id:/
      File.delete(path)
      puts "    Removido: #{File.basename(path)}"
    else
      puts "    Mantido (sem wp_id): #{File.basename(path)}"
    end
  end
end

# Serializa um valor escalar string como YAML seguro.
# Usa aspas duplas quando o valor contém caracteres especiais.
YAML_SPECIAL = /[:#\{\}\[\],|>&*?!%@`"'\\]|\A[-\s]|\s\z|\A(true|false|null|~|\d+)\z/i.freeze

def yaml_scalar(val)
  return '""' if val.nil? || val.empty?

  if val =~ YAML_SPECIAL || val.include?("\n")
    val.inspect  # gera "string com escaping Ruby" — válido em YAML
  else
    val
  end
end

# Serializa o hash de frontmatter em YAML com bloco de início/fim "---"
# Garante que campos nulos apareçam como chave vazia (ex: "km:\n")
def render_frontmatter(hash)
  lines = ["---"]

  hash.each do |key, val|
    case val
    when nil
      lines << "#{key}:"
    when Array
      if val.empty?
        lines << "#{key}: []"
      else
        lines << "#{key}:"
        val.each { |item| lines << "  - #{yaml_scalar(item.to_s)}" }
      end
    when String
      lines << "#{key}: #{yaml_scalar(val)}"
    else
      lines << "#{key}: #{val}"
    end
  end

  lines << "---"
  lines.join("\n") + "\n"
end

def write_md(path, frontmatter, body = nil)
  content = render_frontmatter(frontmatter)
  content += "\n#{body.strip}\n" if body && !body.strip.empty?
  File.write(path, content)
end

# ---------------------------------------------------------------------------
# Import: Carros
# ---------------------------------------------------------------------------

def import_carros
  puts "\n==> Importando carros..."

  carros        = wp_get_all('/carro', _embed: 1)
  total         = carros.size
  imported      = 0
  seen_slugs    = Set.new

  puts "    #{total} carro(s) encontrado(s) na API"

  carros.each_with_index do |carro, idx|
    raw_slug = carro['slug'].to_s.strip
    raw_slug = "carro-#{carro['id']}" if raw_slug.empty?

    # Detectar slug duplicado
    slug = raw_slug
    if seen_slugs.include?(slug)
      slug = "#{raw_slug}-#{carro['id']}"
      warn "  AVISO: slug duplicado '#{raw_slug}', renomeado para '#{slug}'"
    end
    seen_slugs << slug

    embedded = carro['_embedded'] || {}

    # Taxonomias
    marca      = first_term(embedded, 'marca')
    modelo     = first_term(embedded, 'modelo')
    cambio     = first_term(embedded, 'cambio')
    combustivel = first_term(embedded, 'combustivel')
    cor        = first_term(embedded, 'cor')
    opcionais  = extract_terms(embedded, 'opcional')

    anos = extract_terms(embedded, 'ano').sort
    ano_str = anos.empty? ? nil : anos.join('/')

    # Título do WordPress (prioridade)
    raw_title = CGI.unescapeHTML(carro.dig('title', 'rendered').to_s).strip
    
    # Título composto (fallback se rendered estiver vazio)
    composed  = [marca, modelo, ano_str].compact.join(' ')
    title     = raw_title.empty? ? (composed.empty? ? slug : composed) : raw_title

    # Imagens
    featured   = featured_url(embedded)
    imagens    = fetch_gallery(carro['id'], featured)

    # Descrição (HTML do WP, usado como body do markdown)
    body = CGI.unescapeHTML(carro.dig('content', 'rendered').to_s).strip

    frontmatter = {
      'wp_id'       => carro['id'],
      'title'       => title.empty? ? slug : title,
      'marca'       => marca,
      'modelo'      => modelo,
      'ano'         => ano_str,
      'km'          => nil,
      'preco'       => nil,
      'cambio'      => cambio,
      'combustivel' => combustivel,
      'cor'         => cor,
      'portas'      => nil,
      'destaque'    => nil,
      'opcionais'   => opcionais,
      'imagens'     => imagens,
    }

    filepath = File.join(CARROS_DIR, "#{slug}.md")
    write_md(filepath, frontmatter, body)

    imported += 1
    puts "  [#{idx + 1}/#{total}] #{slug}"
  rescue => e
    warn "  ERRO ao importar carro ID #{carro['id']}: #{e.message}"
  end

  imported
end

# ---------------------------------------------------------------------------
# Import: Banners
# ---------------------------------------------------------------------------

def import_banners
  puts "\n==> Importando banners..."

  banners  = wp_get_all('/banner', _embed: 1)
  total    = banners.size
  imported = 0

  puts "    #{total} banner(s) encontrado(s) na API"

  banners.each_with_index do |banner, idx|
    slug = banner['slug'].to_s.strip
    slug = "banner-#{banner['id']}" if slug.empty?

    embedded  = banner['_embedded'] || {}
    imagem    = featured_url(embedded)
    title     = CGI.unescapeHTML(banner.dig('title', 'rendered').to_s).strip

    frontmatter = {
      'wp_id'     => banner['id'],
      'title'     => title.empty? ? slug : title,
      'imagem'    => imagem,
      'link'      => nil,
      'cta'       => nil,
      'subtitulo' => nil,
      'ativo'     => true,
      'ordem'     => idx + 1,
    }

    filepath = File.join(BANNERS_DIR, "#{slug}.md")
    write_md(filepath, frontmatter)

    imported += 1
    puts "  [#{idx + 1}/#{total}] #{slug}"
  rescue => e
    warn "  ERRO ao importar banner ID #{banner['id']}: #{e.message}"
  end

  imported
end

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_import
  FileUtils.mkdir_p(CARROS_DIR)
  FileUtils.mkdir_p(BANNERS_DIR)

  puts '==> Limpando arquivos gerados anteriormente...'
  puts "    _carros/:"
  clean_wp_files(CARROS_DIR)
  puts "    _banners/:"
  clean_wp_files(BANNERS_DIR)

  carros_importados  = import_carros
  banners_importados = import_banners

  puts "\n==> Concluído!"
  puts "    Carros importados : #{carros_importados}"
  puts "    Banners importados: #{banners_importados}"
  
  {
    carros: carros_importados,
    banners: banners_importados
  }
end

if __FILE__ == $0
  run_import
  puts "\nPróximo passo: bundle exec jekyll serve"
end
