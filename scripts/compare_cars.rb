require 'net/http'
require 'json'
require 'yaml'
require 'set'

API_BASE   = ENV['WP_API_BASE'] || 'https://gabrielcanowp-djfpn.wpcomstaging.com/wp-json/wp/v2'
ROOT_DIR   = File.expand_path('..', __dir__)
CARROS_DIR = File.join(ROOT_DIR, '_carros')

def wp_get_all(path)
  uri = URI("#{API_BASE}#{path}")
  params = { per_page: 100 }
  uri.query = URI.encode_www_form(params)
  
  response = Net::HTTP.get_response(uri)
  return [] unless response.is_a?(Net::HTTPSuccess)
  
  JSON.parse(response.body)
end

def get_local_cars
  cars = {}
  Dir.glob(File.join(CARROS_DIR, '*.md')).each do |path|
    begin
      content = File.read(path)
      # Extract wp_id from frontmatter
      if content =~ /^wp_id:\s*(\d+)/
        wp_id = $1.to_i
        cars[wp_id] = File.basename(path)
      else
        cars[path] = File.basename(path) # Use path for non-wp cars
      end
    rescue => e
      warn "Erro ao ler #{path}: #{e.message}"
    end
  end
  cars
end

def compare
  puts "Buscando carros no WordPress..."
  wp_cars = wp_get_all('/carro')
  wp_ids = wp_cars.map { |c| c['id'] }.to_set
  wp_map = wp_cars.each_with_object({}) { |c, h| h[c['id']] = c['slug'] }

  puts "Lendo carros locais em _carros/..."
  local_cars = get_local_cars
  local_wp_ids = local_cars.keys.select { |k| k.is_a?(Integer) }.to_set

  puts "\n--- RESULTADO DA COMPARAÇÃO ---\n"

  # No WordPress mas não locais
  missing_locally = wp_ids - local_wp_ids
  if missing_locally.empty?
    puts "✅ Todos os carros do WordPress estão presentes localmente (com wp_id)."
  else
    puts "❌ Carros no WordPress que NÃO ESTÃO localmente (#{missing_locally.size}):"
    missing_locally.each do |id|
      puts "   - ID: #{id} | Slug: #{wp_map[id]}"
    end
  end

  # Locais mas não no WordPress
  only_locally = []
  local_cars.each do |key, filename|
    if key.is_a?(Integer)
      unless wp_ids.include?(key)
        only_locally << "#{filename} (wp_id: #{key})"
      end
    else
      only_locally << "#{filename} (sem wp_id)"
    end
  end

  if only_locally.empty?
    puts "\n✅ Não há carros locais extras."
  else
    puts "\n❌ Carros locais que NÃO ESTÃO no WordPress (#{only_locally.size}):"
    only_locally.each do |info|
      puts "   - #{info}"
    end
  end
end

compare
