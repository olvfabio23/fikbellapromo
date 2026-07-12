# Deploy no Render - Modulo de Promocoes (5 dias)

## 1) Variaveis de ambiente

Configure no serviço web:

- `DATABASE_URL` (PostgreSQL do Render)
- `ADMIN_TOKEN` (token forte)
- `PROMOTION_TTL_DAYS=5`
- `PROMOTION_TABLE_NAME=fikbella_promocoes`
- `PROMOTION_DB_SCHEMA=` (opcional para schema dedicado)
- `AUTO_INIT_DB=true`

Observacao de seguranca:

- O modulo usa apenas a tabela configurada em `PROMOTION_TABLE_NAME`.
- Nao ha `DROP`, `TRUNCATE` ou migracao destrutiva nos scripts.
- Para banco compartilhado, prefira schema dedicado e token admin forte.

Se usar automacao:

- `API_BASE_URL=https://seu-app.onrender.com`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `WHATSAPP_WEBHOOK_URL` (opcional)
- `FACEBOOK_WEBHOOK_URL` (opcional)

## 2) Comando de inicializacao do web service

Use um comando WSGI padrao, por exemplo:

`gunicorn app:app`

Opcional antes do primeiro deploy (uma vez):

`python scripts/init_promotions_db.py`

## 3) Cron job de limpeza diaria

Crie um Cron Job no Render com:

- Comando: `python scripts/cleanup_expired_promotions.py`
- Frequencia: diaria (1x por dia)

## 4) Cron job de divulgacao

Opcionalmente crie outro Cron Job:

- Comando: `python scripts/distribute_promotions.py`
- Frequencia: conforme estrategia (ex.: a cada 6h)

## 5) Rotas principais

- Vitrine: `/promocoes`
- API publica: `/api/promocoes`
- Admin: `/admin/promocoes?token=SEU_TOKEN`
