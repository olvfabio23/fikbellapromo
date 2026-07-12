"""
Remove promocoes expiradas do banco.
Uso recomendado em cron diario no Render.
"""
from app import app, limpar_promocoes_expiradas


if __name__ == '__main__':
    with app.app_context():
        total = limpar_promocoes_expiradas()
        print(f'Promocoes expiradas removidas: {total}')
