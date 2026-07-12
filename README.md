# 🎨 Fikbella Promo - Gerador de Flyers Promocionais

Programa automatizado para criar flyers promocionais a partir de links de e-commerce.

## 🚀 Funcionalidades

- ✅ Extrai automaticamente informações de produtos (nome completo, preços, imagem)
- ✅ Suporta **Mercado Livre** (scraping automático)
- ✅ Suporta **Shopee** (modo semi-automático)
- ✅ Gera flyers profissionais com design Fikbella clean
- ✅ Card branco com bordas arredondadas
- ✅ **Calcula automaticamente o percentual de desconto**
- ✅ **Destaque em negrito nos preços**
- ✅ **Call-to-action destacado**: "COMPRE PELO LINK"
- ✅ Formato otimizado para Stories do Instagram (1080x1920)
- ✅ Compatível com envio no WhatsApp
- ✅ Salva em alta qualidade PNG

## 📦 Instalação

1. **Instalar Python** (se ainda não tiver): [python.org](https://www.python.org/downloads/)

2. **Instalar dependências**:
```powershell
cd C:\MeusTrabalhos\Projetos\FikbellaPromo
pip install -r requirements.txt
```

## 🎯 Como Usar

### Método 1: Mercado Livre (Automático)
```powershell
python main.py "https://produto.mercadolivre.com.br/MLB-XXXXXXX-nome-produto"
```

### Método 2: Shopee (Semi-automático)
```powershell
python main.py "https://shopee.com.br/produto-i.XXXXX.XXXXX"
```
O programa vai pedir para você digitar:
- Nome do produto
- Preço original (se houver)
- Preço atual
- URL da imagem (clique direito na imagem do produto → "Copiar endereço da imagem")

### Método 3: Modo manual (qualquer plataforma)
```powershell
python demo.py
```
Digite manualmente as informações do produto.

## 📁 Estrutura do Projeto

```
FikbellaPromo/
├── main.py              # Programa principal
├── scraper.py           # Extração de dados dos sites
├── flyer_generator.py   # Geração dos flyers
├── requirements.txt     # Dependências
├── assets/              # Logo e recursos
│   └── logo.png        # Logo da Fikbella
└── output/             # Flyers gerados
    └── flyer_fikbella_YYYYMMDD_HHMMSS.png
```

## 🎨 Cores da Marca

- **Roxo Escuro**: #4B3663 (fundo principal)
- **Roxo Médio**: #8E5BA6 (acentos)
- **Rosa**: #E78EB0 (destaques e preços)
- **Branco**: #FFFFFF (textos)

## ⚠️ Notas Importantes

- Os flyers são salvos na pasta `output/`
- Cada flyer tem um nome único com data e hora
- O logo deve estar em `assets/logo.png` para aparecer no flyer
- O programa baixa temporariamente a imagem do produto e a remove após gerar o flyer

## 🔧 Personalização

Você pode editar `flyer_generator.py` para:
- Alterar tamanho do flyer (padrão: 1080x1080)
- Modificar cores da marca
- Ajustar posicionamento dos elementos
- Adicionar novos elementos decorativos

## 📞 Suporte

Para problemas ou dúvidas, verifique se:
1. Todas as dependências estão instaladas
2. O link do produto está correto e acessível
3. Você tem conexão com a internet

---

Criado em: 16 de dezembro de 2025

---

## Upgrade: Sistema de Promocoes com Validade Automatica (5 dias)

Este projeto agora possui um modulo de promocoes integrado ao Flask com API, painel admin e expiração automatica.

### Novas rotas

- `GET /promocoes`: vitrine publica de promocoes ativas
- `GET /promocoes/<slug>`: pagina interna da promocao
- `GET /r/<id>`: redirecionamento para link afiliado (contabiliza clique)
- `GET /api/promocoes`: lista de promocoes ativas (JSON)
- `GET /admin/promocoes?token=SEU_TOKEN`: painel admin
- `POST /api/admin/promocoes`: cria promocao (requer token)
- `DELETE /api/admin/promocoes/<id>`: exclui promocao (requer token)
- `POST /api/admin/promocoes/cleanup`: remove expiradas manualmente (requer token)

### Banco de dados

Tabela `promocoes` criada automaticamente com campos principais:

- `id`
- `titulo`
- `preco`
- `imagem`
- `link_afiliado`
- `data_publicacao`
- `expira_em`

Por padrao, a validade e de 5 dias (`PROMOTION_TTL_DAYS=5`).

### Variaveis de ambiente

Use o arquivo `.env.example` como base.

Obrigatorias para producao:

- `DATABASE_URL` (PostgreSQL Render)
- `ADMIN_TOKEN` (token forte para rotas administrativas)

### Scripts operacionais

- `python scripts/cleanup_expired_promotions.py`
    - remove promocoes vencidas (ideal para cron diario no Render)
- `python scripts/distribute_promotions.py`
    - distribui promocoes ativas para Telegram e webhooks de WhatsApp/Facebook

### Exemplo de criacao via API

```bash
curl -X POST "http://localhost:5000/api/admin/promocoes?token=SEU_TOKEN" \
    -F "titulo=Tenis Corrida X" \
    -F "preco=R$ 199,90" \
    -F "imagem=https://site.com/img.jpg" \
    -F "link_afiliado=https://afiliado.com/oferta"
```
