# 📋 Histórico de Desenvolvimento - FikbellaPromo

**Data:** 12 de julho de 2026  
**Projeto:** Sistema de Promoções Fikbella com Auto-expirção e Admin Panel

---

## 🎯 Objetivo do Projeto

Criar uma plataforma web completa para gerenciar e exibir promoções de produtos de e-commerce com:
- Sistema de expiração automática (5 dias)
- Painel administrativo com token de segurança
- Auto-preenchimento de dados de produtos via scraping
- Sistema de cupons de desconto
- Integração com WhatsApp para divulgação
- Filtros por loja (Mercado Livre, Shopee, Magalu, Amazon)
- Deploy automatizado no Render.com

---

## 🚀 Funcionalidades Implementadas

### 1. **Sistema de Promoções com Validade**
- ✅ Banco de dados PostgreSQL (Render)
- ✅ Modelo `Promocao` com campos: título, preço, imagem, link afiliado, datas
- ✅ Expiração automática de 5 dias (configurável via `PROMOTION_TTL_DAYS`)
- ✅ Slugs únicos para URLs amigáveis
- ✅ Contador de cliques em links de afiliados

### 2. **Painel Administrativo**
- ✅ Autenticação via token (`ADMIN_TOKEN` environment variable)
- ✅ Interface para criar, visualizar e excluir promoções
- ✅ Auto-preenchimento de dados via URL do produto
- ✅ Sistema de cupons reutilizáveis (percentual ou valor fixo)
- ✅ Preview de preços com desconto aplicado
- ✅ Limpeza manual de promoções expiradas

### 3. **Extração Automática de Dados**
- ✅ Scraping com BeautifulSoup + lxml + requests
- ✅ Suporte para múltiplas plataformas:
  - Mercado Livre (scraping funcional)
  - Shopee (bloqueado - requer entrada manual)
  - Magazine Luiza (bloqueado - requer entrada manual)
  - Amazon (parcial)
- ✅ Extração de:
  - Título do produto
  - Preço atual e original
  - Imagem do produto
  - Identificação automática da loja
- ✅ Fallbacks inteligentes:
  - Parsing de JSON-LD
  - Meta tags Open Graph
  - Regex para preços no HTML
  - Extração de título da URL quando scraping falha
  - Filtro de títulos de erro (páginas bloqueadas)

### 4. **Sistema de Cupons**
- ✅ Cadastro de cupons pelo admin
- ✅ Tipos: percentual (%) ou valor fixo (R$)
- ✅ Preview ao vivo do preço com desconto
- ✅ Armazenamento em JSON local (`saved_admin_coupons.json`)
- ✅ **Cupom copiável**: clicar no cupom copia automaticamente o código
- ✅ Notificação visual ao copiar

### 5. **Sistema de Lojas**
- ✅ Identificação automática da loja pelo domínio
- ✅ Logos personalizados por loja:
  - Mercado Livre (🟡 mercado_livre.png)
  - Shopee (🟠 shopee.png)
  - Magalu (💙 Magalu.png)
  - Amazon (📦 Amazon.jpg)
- ✅ Filtro de promoções por loja
- ✅ Página dedicada por loja: `/promocoes/loja/<slug>`
- ✅ Logos clicáveis que levam ao filtro da loja
- ✅ Símbolos emoji como fallback

### 6. **Interface Pública**
- ✅ Vitrine de promoções ativas: `/promocoes`
- ✅ Página de detalhe: `/promocoes/<slug>`
- ✅ Grid responsivo (mobile/tablet/desktop)
- ✅ Cards com:
  - Imagem do produto (aspect-ratio 1:1)
  - Logo da loja (chip no canto superior)
  - Preço riscado + preço final
  - Badge de desconto
  - **Box de cupom gradiente roxo (copiável)**
  - Botões de ação
- ✅ **Cards alinhados no topo** (não esticam verticalmente)
- ✅ **Horário no timezone de São Paulo/Brasil** (America/Sao_Paulo)

### 7. **Integração WhatsApp**
- ✅ Banner destacado na página inicial
- ✅ Box de CTA em cada promoção
- ✅ Link configurável via `WHATSAPP_GROUP_URL`
- ✅ Destaque verde chamativo

### 8. **Deploy e Infraestrutura**
- ✅ Deploy no Render.com com PostgreSQL
- ✅ Auto-deploy do GitHub (branch `main`)
- ✅ Variáveis de ambiente:
  - `DATABASE_URL`: PostgreSQL connection
  - `ADMIN_TOKEN`: autenticação admin
  - `WHATSAPP_GROUP_URL`: link do grupo
  - `PROMOTION_TTL_DAYS`: validade das promoções
  - `AUTO_INIT_DB`: inicialização automática do banco
- ✅ Python 3.11 (runtime.txt)
- ✅ Gunicorn para produção

---

## 🔧 Problemas Resolvidos Durante o Desenvolvimento

### 1. **Deploy Render Falhando**
- **Problema**: App crashava no startup devido a imports de módulos ausentes
- **Solução**: Wrap em try/except para `scraper.py` e `flyer_generator.py`

### 2. **Logos Não Aparecendo**
- **Problema**: `url_for('static', filename=...)` gerado fora de request context
- **Tentativa 1**: Usar `/static/arquivo.png` direto → não funcionou
- **Solução Final**: Retornar apenas nome do arquivo em `extrair_loja_logo()`, montar caminho completo em `montar_meta_loja()`

### 3. **Mercado Livre Não Detectado**
- **Problema**: Só detectava `mercadolivre.com.br`, mas URLs tinham `produto.mercadolivre.com.br` ou `mercadolibre.com.br`
- **Solução**: Adicionar variações: `mercadolivre`, `mercadolibre`, `mlb`

### 4. **Shopee/Magalu Bloqueados**
- **Problema**: Scraping retorna páginas de erro/login
- **Tentativas**:
  - APIs internas da Shopee → bloqueadas (erro 90309999)
  - Jina.ai reader → resultado parcial
  - Headers alternativos → ainda bloqueado
- **Solução**: 
  - Filtrar títulos de erro conhecidos
  - Extrair título da URL como fallback
  - Permitir entrada manual de dados faltantes
  - Campo `campos_faltantes` na resposta da API

### 5. **Horário Incorreto**
- **Problema**: Datas em UTC não correspondem ao horário de São Paulo
- **Solução**: 
  - Adicionar `pytz` ao requirements.txt
  - Criar função `formatar_data_br()` que converte UTC → America/Sao_Paulo
  - Passar `data_formatada` nos dicionários de view

### 6. **Cards Desalinhados**
- **Problema**: Cards de alturas diferentes ficavam esticados verticalmente
- **Solução**: Adicionar `align-items: start` no grid CSS

### 7. **Cupom Sem Destaque**
- **Problema**: Cupom aparecia apenas como texto junto com desconto
- **Solução**: 
  - Criar box gradiente roxo separado
  - Tornar clicável com função JavaScript
  - Copiar para clipboard com feedback visual

---

## 📁 Estrutura do Projeto

```
FikbellaPromo/
├── app.py                          # Aplicação Flask principal
├── requirements.txt                # Dependências Python
├── runtime.txt                     # Python 3.11
├── render.yaml                     # Configuração Render
├── .env.example                    # Template de variáveis
├── .gitignore                      # Arquivos ignorados
├── DEPLOY_PROMOCOES_RENDER.md      # Guia de deploy
├── README.md                       # Documentação geral
├── HISTORICO_DESENVOLVIMENTO.md    # Este arquivo
│
├── static/                         # Assets estáticos
│   ├── mercado_livre.png           # Logo Mercado Livre
│   ├── shopee.png                  # Logo Shopee
│   ├── Magalu.png                  # Logo Magazine Luiza
│   ├── Amazon.jpg                  # Logo Amazon
│   └── ...                         # Outros assets
│
├── templates/                      # Templates Jinja2
│   ├── promotions.html             # Vitrine de promoções
│   ├── promotion_detail.html       # Detalhe da promoção
│   └── admin_promotions.html       # Painel admin
│
├── scripts/                        # Scripts operacionais
│   ├── cleanup_expired_promotions.py
│   └── distribute_promotions.py
│
├── database/                       # Diretório de dados locais
└── saved_admin_coupons.json        # Cupons salvos
```

---

## 🛠️ Stack Tecnológico

### Backend
- **Flask 3.0.3**: Framework web
- **SQLAlchemy 3.1.1**: ORM
- **PostgreSQL**: Banco de dados (Render)
- **Gunicorn 22.0.0**: WSGI server para produção
- **psycopg2-binary 2.9.9**: Driver PostgreSQL

### Scraping & Data
- **requests 2.31.0**: HTTP client
- **BeautifulSoup4 4.12.2**: HTML parsing
- **lxml 4.9.3**: Parser rápido
- **pytz 2024.1**: Timezone handling

### Frontend
- **HTML5 + CSS3**: Vanilla (sem frameworks)
- **JavaScript**: Vanilla (copy to clipboard, preview)
- **Design**: Custom CSS com variáveis CSS, grid, flexbox
- **Responsivo**: Mobile-first com breakpoints

---

## 🎨 Design System

### Paleta de Cores
```css
--violet: #6366f1;     /* CTA primário */
--ink: #1e293b;        /* Texto principal */
--muted: #64748b;      /* Texto secundário */
--line: #e2e8f0;       /* Bordas */
--panel: #f8fafc;      /* Fundo de painéis */
--green: #25D366;      /* WhatsApp */
```

### Componentes Principais
- **Card de Promoção**: Grid responsivo, imagem quadrada, chip de loja
- **Box de Cupom**: Gradiente roxo (#667eea → #764ba2), hover com elevação
- **Store Filter**: Pills horizontais com logos
- **WhatsApp Banner/Box**: Verde, CTAs destacados

---

## 🔄 Fluxo de Dados

### Criação de Promoção (Admin)
```
1. Admin acessa /admin/promocoes?token=XXX
2. Cola URL do produto
3. Clica "Preencher pelo link"
   → POST /api/admin/promocoes/extract
   → extrair_dados_produto() scraping
   → Retorna JSON com dados + campos_faltantes
4. Admin revisa/completa dados
5. (Opcional) Seleciona cupom cadastrado
   → applyCouponPreview() calcula desconto
6. Clica "Salvar promoção"
   → POST /api/admin/promocoes
   → Cria Promocao no banco
   → expira_em = data_publicacao + 5 dias
```

### Visualização Pública
```
1. Visitante acessa /promocoes
   → buscar_promocoes_ativas() filtra não expiradas
   → montar_promocoes_view() monta dados + data_formatada
   → montar_lojas_disponiveis() lista lojas únicas
   → Renderiza promotions.html
2. Clica em logo da loja
   → /promocoes/loja/<slug>
   → Mesma lógica + filtro por loja
3. Clica "Pegar promoção"
   → /r/<id> (redirect tracker)
   → Incrementa contador de cliques
   → Redireciona para link_afiliado
```

---

## 🌐 Rotas da Aplicação

### Públicas
- `GET /promocoes` - Vitrine de todas as promoções ativas
- `GET /promocoes/loja/<slug>` - Promoções filtradas por loja
- `GET /promocoes/<slug>` - Detalhe de uma promoção
- `GET /r/<id>` - Redirect tracker para link afiliado
- `GET /api/promocoes` - API JSON com promoções ativas

### Administrativas (requerem `?token=XXX`)
- `GET /admin/promocoes` - Painel admin
- `POST /api/admin/promocoes` - Criar promoção
- `DELETE /api/admin/promocoes/<id>` - Excluir promoção
- `POST /api/admin/promocoes/extract` - Auto-fill de produto
- `POST /api/admin/promocoes/cleanup` - Limpar expiradas
- `GET /api/admin/coupons` - Listar cupons
- `POST /api/admin/coupons` - Cadastrar cupom

### Legacy (fallbacks)
- `GET /` - Redirect para /promocoes
- `POST /generate` - Gerador de flyers (módulo opcional)

---

## 🔐 Variáveis de Ambiente

```bash
# Obrigatórias para produção
DATABASE_URL=postgresql://user:pass@host:port/db
ADMIN_TOKEN=seu_token_seguro_aqui

# Opcionais (com defaults)
WHATSAPP_GROUP_URL=https://chat.whatsapp.com/LSlj4MmAyMODcyW7us4vCY
PROMOTION_TTL_DAYS=5
AUTO_INIT_DB=true
```

---

## 📊 Modelo de Dados

### Tabela `promocoes`
```python
class Promocao(db.Model):
    id: int (PK, auto-increment)
    titulo: str(300)
    preco: str(1000)  # JSON: {preco_final, preco_original, desconto_texto, cupom_nome}
    imagem: str(500)
    link_afiliado: str(500)
    slug: str(320, unique)
    data_publicacao: datetime
    expira_em: datetime
    total_cliques: int (default 0)
    ultimo_clique_em: datetime (nullable)
```

### Formato de Preço (JSON)
```json
{
  "preco_final": "R$ 159,90",
  "preco_original": "R$ 199,90",
  "desconto_texto": "-20%",
  "cupom_nome": "FIKBELLA10"
}
```

### Cupons Salvos (JSON local)
```json
[
  {
    "nome": "FIKBELLA10",
    "tipo": "percentual",
    "valor": 10
  },
  {
    "nome": "DESC50",
    "tipo": "fixo",
    "valor": 50.0
  }
]
```

---

## 🚢 Deploy no Render

### Processo
1. Conectar repositório GitHub
2. Configurar variáveis de ambiente
3. Render detecta runtime.txt → Python 3.11
4. Instala requirements.txt
5. Cria PostgreSQL database
6. Injeta DATABASE_URL
7. Executa gunicorn app:app

### Auto-deploy
- Cada `git push origin main` → rebuild automático
- Processo leva ~2-3 minutos
- Zero downtime com health checks

---

## 📝 Histórico de Commits Principais

```
358e10f - feat: cupom copiavel, timezone SP, alinhamento cards e fix logo Mercado Livre
6c5392d - fix: logo display with static paths and filter blocked site error titles
54a6fb8 - fix: store logo paths and improve URL-based title extraction for blocked sites
4ffdf67 - feat: clickable store logos and store-filtered promotion pages
[commits anteriores de setup inicial, scraping, admin panel, etc.]
```

---

## 🐛 Limitações Conhecidas

### 1. **Scraping Bloqueado**
- **Shopee**: Retorna página de login, API bloqueada
- **Magazine Luiza**: Error 403 em todas as requisições
- **Workaround**: Entrada manual de dados faltantes

### 2. **Preços sem Validação**
- Sistema aceita qualquer formato de preço
- Não valida se preço final < preço original

### 3. **Imagens Externas**
- Não faz cache/upload de imagens
- Depende de URLs externas (podem quebrar)

### 4. **Limpeza Manual**
- Expiração automática só remove da query
- Limpeza física requer script ou botão admin

### 5. **Sem Paginação**
- Lista todas as promoções em uma página
- Pode ficar lento com muitos registros

---

## 🔮 Possíveis Melhorias Futuras

### Performance
- [ ] Paginação ou scroll infinito
- [ ] Cache de queries com Redis
- [ ] Lazy loading de imagens

### Funcionalidades
- [ ] Categorias de produtos
- [ ] Busca por palavra-chave
- [ ] Notificações push (PWA)
- [ ] Sistema de favoritos
- [ ] Compartilhamento social (meta tags)
- [ ] Analytics de cliques por promoção

### Admin
- [ ] Edição de promoções existentes
- [ ] Upload de imagens ao servidor
- [ ] Dashboard com estatísticas
- [ ] Múltiplos usuários admin
- [ ] Agendamento de publicações

### Scraping
- [ ] Usar Playwright/Selenium para sites bloqueados
- [ ] Proxy rotation
- [ ] Rate limiting inteligente
- [ ] Atualização automática de preços

### UX
- [ ] Dark mode
- [ ] Animações de transição
- [ ] Skeleton loaders
- [ ] Toast notifications
- [ ] Confirmação antes de excluir

---

## 📚 Aprendizados e Boas Práticas

### 1. **Graceful Degradation**
- Sistema funciona mesmo quando scraping falha
- Fallbacks em múltiplas camadas (JSON-LD → meta tags → regex → URL)
- Nunca travar o fluxo do usuário

### 2. **Environment-based Config**
- Tudo configurável via variáveis de ambiente
- Defaults sensatos para desenvolvimento local
- Secrets nunca no código

### 3. **Timezone Awareness**
- Sempre armazenar UTC no banco
- Converter para timezone do usuário na apresentação
- Usar biblioteca confiável (pytz)

### 4. **Error Handling**
- Try/except em imports opcionais
- Mensagens de erro claras para o usuário
- Logs informativos para debugging

### 5. **Progressive Enhancement**
- HTML semântico primeiro
- CSS para layout e estilo
- JavaScript para interatividade (não essencial)

---

## 🤝 Contribuições e Manutenção

### Como Adicionar Nova Loja

1. **Backend** (app.py):
```python
# Em extrair_loja_nome()
mapa = {
    # ... existentes ...
    'novaoja': 'Nome da Nova Loja',
}

# Em extrair_loja_simbolo()
mapa = {
    # ... existentes ...
    'novaoja': '🔵',
}

# Em extrair_loja_logo()
mapa = {
    # ... existentes ...
    'novaoja': 'novaoja.png',
}
```

2. **Static**: Adicionar `static/novaoja.png`

3. **Deploy**: Commit e push → auto-deploy

### Como Testar Localmente

```bash
cd C:\MeusTrabalhos\Projetos\FikbellaPromo

# Criar .env com variáveis necessárias
DATABASE_URL=postgresql://localhost/fikbella
ADMIN_TOKEN=test123

# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
python app.py

# Acessar
http://localhost:5000/promocoes
http://localhost:5000/admin/promocoes?token=test123
```

---

## 📞 Informações do Projeto

- **Repositório**: https://github.com/olvfabio23/fikbellapromo
- **Deploy**: https://fikbellapromo.onrender.com (ou URL configurada)
- **WhatsApp**: https://chat.whatsapp.com/LSlj4MmAyMODcyW7us4vCY
- **Framework**: Flask 3.0.3 + PostgreSQL
- **Hospedagem**: Render.com
- **Última Atualização**: 12/07/2026

---

## ✅ Checklist de Funcionalidades

### Core
- [x] CRUD de promoções
- [x] Expiração automática (5 dias)
- [x] Slugs únicos
- [x] Contador de cliques

### Admin
- [x] Autenticação por token
- [x] Interface de gestão
- [x] Auto-fill de dados
- [x] Sistema de cupons
- [x] Preview de preços

### Frontend
- [x] Vitrine responsiva
- [x] Página de detalhe
- [x] Filtro por loja
- [x] Logos clicáveis
- [x] Cupom copiável
- [x] Horário correto (SP)
- [x] Cards alinhados

### Integração
- [x] WhatsApp CTAs
- [x] Links de afiliados
- [x] Tracking de cliques

### Deploy
- [x] Render.com
- [x] PostgreSQL
- [x] Auto-deploy GitHub
- [x] Environment variables
- [x] Production-ready

---

## 🎓 Conclusão

O projeto **FikbellaPromo** foi desenvolvido com foco em:
- **Usabilidade**: Interface intuitiva para admin e visitantes
- **Confiabilidade**: Fallbacks e graceful degradation
- **Performance**: Deploy otimizado, queries eficientes
- **Manutenibilidade**: Código limpo, bem documentado
- **Escalabilidade**: Arquitetura preparada para crescimento

Todas as funcionalidades solicitadas foram implementadas com sucesso, incluindo soluções criativas para limitações técnicas (scraping bloqueado, timezone, logos).

---

**Desenvolvido com dedicação para Fikbella** 💜
