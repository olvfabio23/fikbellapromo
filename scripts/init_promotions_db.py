"""
Inicializa apenas as estruturas do modulo de promocoes.
Seguro para banco compartilhado: cria tabelas ausentes sem remover/alterar tabelas existentes.
"""
from app import app, init_promotions_db


if __name__ == '__main__':
    with app.app_context():
        init_promotions_db()
        print('Tabela de promocoes verificada/criada com sucesso.')
