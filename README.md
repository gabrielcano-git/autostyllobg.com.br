# Auto Styllo BG

Site institucional da Auto Styllo BG.

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
