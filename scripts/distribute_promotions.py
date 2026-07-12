"""
Distribui promocoes ativas para canais externos.
- Telegram: envio nativo via Bot API
- WhatsApp/Facebook: opcional via webhook
"""
import os
import requests


API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
WHATSAPP_WEBHOOK_URL = os.getenv('WHATSAPP_WEBHOOK_URL', '')
FACEBOOK_WEBHOOK_URL = os.getenv('FACEBOOK_WEBHOOK_URL', '')


def get_promocoes_ativas():
    resp = requests.get(f'{API_BASE_URL}/api/promocoes', timeout=20)
    resp.raise_for_status()
    return resp.json()


def formatar_mensagem(promocao):
    return (
        f"{promocao['titulo']}\n"
        f"Preco: {promocao['preco']}\n"
        f"Veja detalhes: {promocao['link_interno']}\n"
        f"Comprar: {promocao['link_redirecionamento']}"
    )


def enviar_telegram(texto):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {'canal': 'telegram', 'status': 'ignorado', 'motivo': 'token/chat_id ausente'}

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    resp = requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': texto}, timeout=20)

    if resp.ok:
        return {'canal': 'telegram', 'status': 'ok'}

    return {'canal': 'telegram', 'status': 'erro', 'detalhe': resp.text[:300]}


def enviar_webhook(url, payload, canal):
    if not url:
        return {'canal': canal, 'status': 'ignorado', 'motivo': 'webhook ausente'}

    resp = requests.post(url, json=payload, timeout=20)
    if resp.ok:
        return {'canal': canal, 'status': 'ok'}

    return {'canal': canal, 'status': 'erro', 'detalhe': resp.text[:300]}


def main():
    promocoes = get_promocoes_ativas()
    if not promocoes:
        print('Nenhuma promocao ativa para divulgar.')
        return

    for promocao in promocoes:
        mensagem = formatar_mensagem(promocao)
        payload = {
            'titulo': promocao['titulo'],
            'preco': promocao['preco'],
            'imagem': promocao['imagem'],
            'link_interno': promocao['link_interno'],
            'link_redirecionamento': promocao['link_redirecionamento'],
            'texto': mensagem,
        }

        resultados = [
            enviar_telegram(mensagem),
            enviar_webhook(WHATSAPP_WEBHOOK_URL, payload, 'whatsapp'),
            enviar_webhook(FACEBOOK_WEBHOOK_URL, payload, 'facebook'),
        ]

        print(f"Promocao ID {promocao['id']}: {resultados}")


if __name__ == '__main__':
    main()
