"""
Aplicação Web Fikbella Promo
Interface web para geração de flyers promocionais
"""
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify, abort
import os
import json
from datetime import datetime, timedelta
import re
from scraper import ProductScraper
from flyer_generator import FlyerGenerator
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'fikbella_promo_secret_key_2024'

database_url = os.getenv('DATABASE_URL', 'sqlite:///fikbella_promotions.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

PROMOTION_TTL_DAYS = int(os.getenv('PROMOTION_TTL_DAYS', '5'))
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'trocar-este-token')
PROMOTION_TABLE_NAME = os.getenv('PROMOTION_TABLE_NAME', 'fikbella_promocoes')
PROMOTION_DB_SCHEMA = os.getenv('PROMOTION_DB_SCHEMA', '')
AUTO_INIT_DB = os.getenv('AUTO_INIT_DB', 'false').lower() == 'true'

COUPONS_FILE = 'saved_coupons.json'


class Promocao(db.Model):
    __tablename__ = PROMOTION_TABLE_NAME
    if PROMOTION_DB_SCHEMA:
        __table_args__ = {'schema': PROMOTION_DB_SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Text, nullable=False)
    imagem = db.Column(db.Text, nullable=False)
    link_afiliado = db.Column(db.Text, nullable=False)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    data_publicacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    expira_em = db.Column(db.DateTime, nullable=False, index=True)
    total_cliques = db.Column(db.Integer, nullable=False, default=0)
    ultimo_clique_em = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'preco': self.preco,
            'imagem': self.imagem,
            'link_afiliado': self.link_afiliado,
            'link_interno': url_for('detalhe_promocao', slug=self.slug, _external=True),
            'link_redirecionamento': url_for('redirect_afiliado', promocao_id=self.id, _external=True),
            'slug': self.slug,
            'data_publicacao': self.data_publicacao.isoformat(),
            'expira_em': self.expira_em.isoformat(),
            'total_cliques': self.total_cliques,
        }


def slugify(texto):
    texto = texto.lower().strip()
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    texto = re.sub(r'[\s-]+', '-', texto)
    return texto.strip('-') or 'promocao'


def gerar_slug_unico(titulo):
    base = slugify(titulo)[:150]
    slug = base
    sufixo = 2

    while Promocao.query.filter_by(slug=slug).first() is not None:
        slug = f"{base}-{sufixo}"
        sufixo += 1

    return slug


def validar_admin_token():
    token = request.headers.get('X-Admin-Token') or request.args.get('token') or request.form.get('token')
    if token != ADMIN_TOKEN:
        abort(401, description='Token administrativo inválido.')


def buscar_promocoes_ativas():
    agora = datetime.utcnow()
    return (
        Promocao.query
        .filter(Promocao.expira_em >= agora)
        .order_by(Promocao.data_publicacao.desc())
        .all()
    )


def limpar_promocoes_expiradas():
    agora = datetime.utcnow()
    expiradas = Promocao.query.filter(Promocao.expira_em < agora).all()
    total = len(expiradas)

    if total:
        for promocao in expiradas:
            db.session.delete(promocao)
        db.session.commit()

    return total


def init_promotions_db():
    db.create_all()


if AUTO_INIT_DB:
    with app.app_context():
        init_promotions_db()

def load_coupons():
    """Carrega cupons salvos"""
    if os.path.exists(COUPONS_FILE):
        try:
            with open(COUPONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_coupon(name, discount):
    """Salva cupom (mantém apenas os 5 últimos)"""
    coupons = load_coupons()
    
    # Remover se já existe
    coupons = [c for c in coupons if c['name'].upper() != name.upper()]
    
    # Adicionar no início
    coupons.insert(0, {'name': name.upper(), 'discount': discount})
    
    # Manter apenas 5
    coupons = coupons[:5]
    
    with open(COUPONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(coupons, f, ensure_ascii=False, indent=2)
    
    return coupons

@app.route('/')
def index():
    """Página inicial com formulário"""
    saved_coupons = load_coupons()
    return render_template('index.html', saved_coupons=saved_coupons)

@app.route('/calculadora-trabalhista')
def calculadora_trabalhista():
    """Página com cálculos trabalhistas"""
    return render_template('calculadora_trabalhista.html')

@app.route('/api/coupons')
def get_coupons():
    """API para obter cupons salvos"""
    return jsonify(load_coupons())


@app.route('/promocoes')
def vitrine_promocoes():
    promocoes = buscar_promocoes_ativas()
    return render_template('promotions.html', promocoes=promocoes)


@app.route('/promocoes/<slug>')
def detalhe_promocao(slug):
    promocao = Promocao.query.filter_by(slug=slug).first_or_404()

    if promocao.expira_em < datetime.utcnow():
        abort(404)

    return render_template('promotion_detail.html', promocao=promocao)


@app.route('/r/<int:promocao_id>')
def redirect_afiliado(promocao_id):
    promocao = Promocao.query.get_or_404(promocao_id)

    if promocao.expira_em < datetime.utcnow():
        flash('Essa promoção expirou.', 'warning')
        return redirect(url_for('vitrine_promocoes'))

    promocao.total_cliques += 1
    promocao.ultimo_clique_em = datetime.utcnow()
    db.session.commit()

    return redirect(promocao.link_afiliado)


@app.route('/api/promocoes')
def api_promocoes():
    promocoes = [p.to_dict() for p in buscar_promocoes_ativas()]
    return jsonify(promocoes)


@app.route('/admin/promocoes')
def admin_promocoes():
    validar_admin_token()
    promocoes = Promocao.query.order_by(Promocao.data_publicacao.desc()).all()
    return render_template('admin_promotions.html', promocoes=promocoes, ttl_dias=PROMOTION_TTL_DAYS)


@app.route('/api/admin/promocoes', methods=['POST'])
def criar_promocao():
    validar_admin_token()

    payload = request.get_json(silent=True) or request.form

    titulo = (payload.get('titulo') or '').strip()
    preco = (payload.get('preco') or '').strip()
    imagem = (payload.get('imagem') or '').strip()
    link_afiliado = (payload.get('link_afiliado') or '').strip()

    if not titulo or not preco or not imagem or not link_afiliado:
        return jsonify({'erro': 'Campos obrigatórios: titulo, preco, imagem, link_afiliado.'}), 400

    data_publicacao = datetime.utcnow()
    promocao = Promocao(
        titulo=titulo,
        preco=preco,
        imagem=imagem,
        link_afiliado=link_afiliado,
        slug=gerar_slug_unico(titulo),
        data_publicacao=data_publicacao,
        expira_em=data_publicacao + timedelta(days=PROMOTION_TTL_DAYS),
    )

    db.session.add(promocao)
    db.session.commit()

    return jsonify({'ok': True, 'promocao': promocao.to_dict()}), 201


@app.route('/api/admin/promocoes/<int:promocao_id>', methods=['DELETE'])
def excluir_promocao(promocao_id):
    validar_admin_token()
    promocao = Promocao.query.get_or_404(promocao_id)
    db.session.delete(promocao)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/promocoes/cleanup', methods=['POST'])
def cleanup_promocoes_api():
    validar_admin_token()
    removidas = limpar_promocoes_expiradas()
    return jsonify({'ok': True, 'removidas': removidas})

@app.route('/generate', methods=['POST'])
def generate_flyer():
    """Processa o formulário e mostra prévia"""
    try:
        # Obter dados do formulário
        platform = request.form.get('platform')
        product_url = request.form.get('product_url')
        coupon_name = request.form.get('coupon_name', '').strip()
        coupon_discount = request.form.get('coupon_discount', '').strip()
        
        # Validar URL
        if not product_url:
            flash('❌ Por favor, insira o link do produto!', 'error')
            return redirect(url_for('index'))
        
        # Processar cupom de desconto
        coupon_data = None
        if coupon_name and coupon_discount:
            try:
                discount_percent = float(coupon_discount)
                if discount_percent > 0 and discount_percent <= 100:
                    coupon_data = {
                        'name': coupon_name.upper(),
                        'discount': discount_percent
                    }
            except ValueError:
                flash('⚠️ Porcentagem de desconto inválida. Continuando sem cupom.', 'warning')
        
        # Scraping do produto
        scraper = ProductScraper()
        
        # Se for Shopee, vai para modo manual
        if 'shopee' in product_url.lower():
            return render_template('manual_input.html', url=product_url, coupon_data=coupon_data)
        
        # Mercado Livre - automático
        product_data = scraper.scrape_product(product_url)
        
        if not product_data:
            flash('❌ Não foi possível extrair dados do produto. Verifique o link.', 'error')
            return redirect(url_for('index'))
        
        # Aplicar cupom de desconto se fornecido
        if coupon_data:
            product_data = apply_coupon_discount(product_data, coupon_data)
            # Salvar cupom usado
            save_coupon(coupon_data['name'], coupon_data['discount'])
        
        # Baixar imagem do produto
        image_path = 'temp_product_image.jpg'
        success = scraper.download_image(product_data['image_url'], image_path)
        
        if not success:
            flash('❌ Erro ao baixar imagem do produto.', 'error')
            return redirect(url_for('index'))
        
        # Gerar prévia
        generator = FlyerGenerator()
        preview_filename = 'preview_temp.png'
        preview_path = os.path.join('static', preview_filename)
        
        generator.create_flyer(product_data, image_path, preview_path)
        
        # Limpar arquivo temporário da imagem
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Mostrar prévia
        return render_template('preview.html', 
                             preview_path=preview_filename,
                             product_data=product_data)
    
    except Exception as e:
        flash(f'❌ Erro ao gerar prévia: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/update_preview', methods=['POST'])
def update_preview():
    """Atualiza a prévia quando o usuário edita dados"""
    try:
        # Obter dados editados via JSON
        data = request.get_json()
        
        name = data.get('name')
        current_price = data.get('current_price')
        original_price = data.get('original_price', '')
        image_url = data.get('image_url')
        platform = data.get('platform', 'Mercado Livre')
        coupon_name = data.get('coupon_name', '')
        coupon_discount = data.get('coupon_discount', '')
        
        # Montar dados do produto
        product_data = {
            'name': name,
            'current_price': current_price,
            'original_price': original_price if original_price else None,
            'image_url': image_url,
            'platform': platform
        }
        
        # Aplicar cupom se houver
        if coupon_name and coupon_discount:
            product_data['coupon'] = {
                'name': coupon_name,
                'discount': float(coupon_discount)
            }
        
        # Baixar imagem
        scraper = ProductScraper()
        image_path = 'temp_preview_update.jpg'
        success = scraper.download_image(image_url, image_path)
        
        if not success:
            return jsonify({'success': False, 'error': 'Erro ao baixar imagem'})
        
        # Gerar nova prévia
        generator = FlyerGenerator()
        preview_filename = 'preview_temp.png'
        preview_path = os.path.join('static', preview_filename)
        
        generator.create_flyer(product_data, image_path, preview_path)
        
        # Limpar arquivo temporário
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Retornar sucesso com timestamp para forçar reload
        import time
        timestamp = int(time.time())
        return jsonify({
            'success': True, 
            'preview_url': f'/static/{preview_filename}?t={timestamp}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate_final', methods=['POST'])
def generate_final():
    """Gera o flyer final após edições na prévia"""
    try:
        # Obter dados editados
        name = request.form.get('name')
        current_price = request.form.get('current_price')
        original_price = request.form.get('original_price', '')
        image_url = request.form.get('image_url')
        platform = request.form.get('platform', 'Mercado Livre')
        coupon_name = request.form.get('coupon_name', '')
        coupon_discount = request.form.get('coupon_discount', '')
        
        # Montar dados do produto
        product_data = {
            'name': name,
            'current_price': current_price,
            'original_price': original_price if original_price else None,
            'image_url': image_url,
            'platform': platform
        }
        
        # Aplicar cupom se houver
        if coupon_name and coupon_discount:
            product_data['coupon'] = {
                'name': coupon_name,
                'discount': float(coupon_discount)
            }
        
        # Baixar imagem
        scraper = ProductScraper()
        image_path = 'temp_product_final.jpg'
        success = scraper.download_image(image_url, image_path)
        
        if not success:
            flash('❌ Erro ao baixar imagem. Verifique o link.', 'error')
            return redirect(url_for('index'))
        
        # Gerar flyer final
        generator = FlyerGenerator()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"flyer_fikbella_{timestamp}.png"
        output_path = os.path.join('output', output_filename)
        
        generator.create_flyer(product_data, image_path, output_path)
        
        # Limpar arquivos temporários
        if os.path.exists(image_path):
            os.remove(image_path)
        if os.path.exists(os.path.join('static', 'preview_temp.png')):
            os.remove(os.path.join('static', 'preview_temp.png'))
        
        flash('✅ Flyer gerado com sucesso!', 'success')
        return render_template('result.html', flyer_path=output_filename, product_data=product_data)
    
    except Exception as e:
        flash(f'❌ Erro ao gerar flyer: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/generate_manual', methods=['POST'])
def generate_manual():
    """Gera prévia com dados inseridos manualmente (Shopee)"""
    try:
        # Obter dados do formulário manual
        name = request.form.get('name').strip()
        current_price = request.form.get('current_price').strip()
        original_price = request.form.get('original_price', '').strip()
        image_url = request.form.get('image_url').strip()
        coupon_name = request.form.get('coupon_name', '').strip()
        coupon_discount = request.form.get('coupon_discount', '').strip()
        
        # Validar dados obrigatórios
        if not name or not current_price or not image_url:
            flash('❌ Nome, preço atual e imagem são obrigatórios!', 'error')
            return redirect(url_for('index'))
        
        # Formatar preços
        if not current_price.startswith('R$'):
            current_price = f"R$ {current_price}".replace('R$ R$', 'R$')
        
        if original_price and not original_price.startswith('R$'):
            original_price = f"R$ {original_price}".replace('R$ R$', 'R$')
        elif not original_price:
            original_price = None
        
        # Montar dados do produto
        product_data = {
            'name': name,
            'current_price': current_price,
            'original_price': original_price,
            'image_url': image_url,
            'platform': 'Shopee'
        }
        
        # Processar cupom de desconto
        if coupon_name and coupon_discount:
            try:
                discount_percent = float(coupon_discount)
                if discount_percent > 0 and discount_percent <= 100:
                    coupon_data = {
                        'name': coupon_name.upper(),
                        'discount': discount_percent
                    }
                    product_data = apply_coupon_discount(product_data, coupon_data)
                    # Salvar cupom usado
                    save_coupon(coupon_data['name'], coupon_data['discount'])
            except ValueError:
                flash('⚠️ Porcentagem de desconto inválida. Continuando sem cupom.', 'warning')
        
        # Baixar imagem
        scraper = ProductScraper()
        image_path = 'temp_product_image_manual.jpg'
        success = scraper.download_image(image_url, image_path)
        
        if not success:
            flash('❌ Erro ao baixar imagem. Verifique o link.', 'error')
            return redirect(url_for('index'))
        
        # Gerar prévia
        generator = FlyerGenerator()
        preview_filename = 'preview_temp.png'
        preview_path = os.path.join('static', preview_filename)
        
        generator.create_flyer(product_data, image_path, preview_path)
        
        # Limpar arquivo temporário
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Mostrar prévia
        return render_template('preview.html', 
                             preview_path=preview_filename,
                             product_data=product_data)
    
    except Exception as e:
        flash(f'❌ Erro ao gerar prévia: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    """Download do flyer gerado"""
    file_path = os.path.join('output', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('❌ Arquivo não encontrado.', 'error')
        return redirect(url_for('index'))

def apply_coupon_discount(product_data, coupon_data):
    """Aplica desconto do cupom no preço do produto"""
    try:
        # Extrair preço atual
        current_price_str = product_data['current_price'].replace('R$', '').replace('.', '').replace(',', '.').strip()
        current_price = float(current_price_str)
        
        # Calcular novo preço com desconto do cupom
        discount_amount = current_price * (coupon_data['discount'] / 100)
        new_price = current_price - discount_amount
        
        # Se não tinha preço original, o atual vira o original
        if not product_data.get('original_price'):
            product_data['original_price'] = product_data['current_price']
        
        # Atualizar preço atual com desconto do cupom
        product_data['current_price'] = f"R$ {new_price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # Adicionar informações do cupom
        product_data['coupon'] = coupon_data
        
        return product_data
    except Exception as e:
        print(f"Erro ao aplicar cupom: {e}")
        return product_data

if __name__ == '__main__':
    # Criar pasta output se não existir
    if not os.path.exists('output'):
        os.makedirs('output')

    with app.app_context():
        init_promotions_db()
        limpar_promocoes_expiradas()
    
    print("="*60)
    print("    FIKBELLA PROMO - Interface Web")
    print("="*60)
    print("\n🌐 Servidor iniciando...")
    print("📱 Acesse: http://localhost:5000")
    print("\n💡 Pressione Ctrl+C para parar o servidor\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
