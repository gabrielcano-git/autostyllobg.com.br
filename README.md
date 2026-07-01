# Auto Styllo BG

Site institucional da Auto Styllo BG.

## Importador WordPress via Cloud Run

O serviço em `scripts/app.py` expõe `POST /import` para importar os carros e banners do WordPress, gerar os arquivos Markdown em `_carros/` e `_banners/`, commitar as alterações na branch `main` e fazer push para o GitHub. Esse push dispara o workflow de GitHub Pages.

### Teste local com Docker

Crie um arquivo `.env` a partir de `.env.example` e preencha os tokens:

```bash
docker compose up importador
curl -X POST http://localhost:8080/import \
  -H "Authorization: Bearer $IMPORT_TOKEN"
```

Variáveis obrigatórias para execução:

- `IMPORT_TOKEN`: token bearer exigido pelo endpoint.
- `GITHUB_TOKEN`: PAT do GitHub com permissão de push no repositório.
- `WP_USER` e `WP_APP_PASSWORD`: credenciais do WordPress, quando a API exigir autenticação.

## Gerenciamento de Banners

Os banners da página inicial são gerenciados de forma dinâmica através de arquivos Markdown localizados na pasta `_banners/`.

### Como criar um novo banner

Para criar um novo banner, crie um arquivo `.md` dentro da pasta `_banners/` (ex: `banner-oferta.md`) com o seguinte conteúdo:

```markdown
---
title: "Os melhores seminovos estão aqui"
subtitulo: "Estoque renovado toda semana. Financiamento facilitado."
imagem: /assets/images/banners/banner-principal.jpg
link: /carros/
cta: "Ver estoque"
ativo: true
ordem: 1
---
```

### Detalhes dos Campos:

- **title**: Título principal que será exibido no banner.
- **subtitulo**: Pequena descrição ou frase de impacto.
- **imagem**: Caminho da imagem que será usada como fundo. Recomenda-se usar imagens de alta resolução.
- **link**: URL para onde o usuário será redirecionado ao clicar no banner.
- **cta**: Texto que aparecerá no botão de ação (Call to Action).
- **ativo**: Define se o banner deve ser exibido (`true`) ou ocultado (`false`).
- **ordem**: Define a prioridade na fila de exibição (números menores aparecem primeiro).
