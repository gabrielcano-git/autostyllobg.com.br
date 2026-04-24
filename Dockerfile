# Use a imagem oficial do Python
FROM python:3.12-slim

# Instale dependências do sistema
RUN apt-get update -qq && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Configura o diretório de trabalho
WORKDIR /app

# Copia as dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Expõe a porta que o Cloud Run usa
EXPOSE 8080

# Usamos gunicorn para produção
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "scripts.app:app"]
