"""
Aplicação Web Fikbella Promo
Interface web para geração de flyers promocionais
"""
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify, abort
import os
import json
from datetime import datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
from flask_sqlalchemy import SQLAlchemy
from jinja2 import TemplateNotFound
from urllib.parse import urlparse
from urllib.parse import urljoin

try:
    from scraper import ProductScraper
    from flyer_generator import FlyerGenerator
    FLYER_MODULES_AVAILABLE = True
except ModuleNotFoundError:
    ProductScraper = None
    FlyerGenerator = None
    FLYER_MODULES_AVAILABLE = False

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
WHATSAPP_GROUP_URL = os.getenv('WHATSAPP_GROUP_URL', 'https://chat.whatsapp.com/LSlj4MmAyMODcyW7us4vCY')

COUPONS_FILE = 'saved_coupons.json'
ADMIN_COUPONS_FILE = 'saved_admin_coupons.json'


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
        preco_info = parse_preco_info(self.preco)
        return {
            'id': self.id,
            'titulo': self.titulo,
            'preco': preco_info['preco_final'],
            'preco_original': preco_info['preco_original'],
            'desconto_texto': preco_info['desconto_texto'],
            'cupom_nome': preco_info['cupom_nome'],
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


def extrair_loja_nome(link):
    try:
        host = (urlparse(link).netloc or '').lower()
    except Exception:
        return 'Loja parceira'

    host = host.replace('www.', '')
    mapa = {
        'mercadolivre': 'Mercado Livre',
        'shopee': 'Shopee',
        'amazon': 'Amazon',
        'magazineluiza': 'Magalu',
        'magalu': 'Magalu',
        'aliexpress': 'AliExpress',
        'shein': 'SHEIN',
        'netshoes': 'Netshoes',
        'centauro': 'Centauro',
    }

    for chave, nome in mapa.items():
        if chave in host:
            return nome

    if host:
        base = host.split('.')
        if base:
            return base[0].capitalize()
    return 'Loja parceira'


def extrair_loja_simbolo(link):
    try:
        host = (urlparse(link).netloc or '').lower().replace('www.', '')
    except Exception:
        return '🛍️'

    mapa = {
        'mercadolivre': '🟡',
        'shopee': '🟠',
        'amazon': '🛒',
        'magazineluiza': '🔵',
        'magalu': '🔵',
        'aliexpress': '🔴',
        'shein': '⚫',
        'netshoes': '🏃',
        'centauro': '⚽',
    }
    for chave, simbolo in mapa.items():
        if chave in host:
            return simbolo
    return '🛍️'


def _normalize_url(product_url):
    url = (product_url or '').strip()
    if not url:
        return ''
    if not re.match(r'^https?://', url, flags=re.IGNORECASE):
        url = f'https://{url}'
    return url


def _expand_short_url(product_url, headers):
    session = requests.Session()
    session.headers.update(headers)

    try:
        resp = session.get(product_url, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        return resp.url, resp.text
    except requests.RequestException:
        pass

    try:
        resp = session.head(product_url, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        return resp.url, ''
    except requests.RequestException:
        return product_url, ''


def _extract_price_candidates(text):
    if not text:
        return []
    candidates = []
    patterns = [
        r'R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}',
        r'\d{1,3}(?:\.\d{3})*,\d{2}\s*R\$',
        r'"price"\s*[:=]\s*"?(\d+(?:\.\d{1,2})?)"?',
        r'"salePrice"\s*[:=]\s*"?(\d+(?:\.\d{1,2})?)"?',
        r'"bestPrice"\s*[:=]\s*"?(\d+(?:\.\d{1,2})?)"?',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            raw = match if isinstance(match, str) else str(match)
            num = _parse_preco_to_float(raw)
            if num is not None and num > 0:
                candidates.append(num)

    return sorted(set(candidates))


def _extract_image_from_html(soup, base_url):
    imagem = (
        _get_meta_content(soup, 'meta[property="og:image"]')
        or _get_meta_content(soup, 'meta[name="twitter:image"]')
    )
    if imagem:
        return imagem

    for selector in ['img#landingImage', 'img[data-old-hires]', 'img[itemprop="image"]', 'img[src]']:
        tag = soup.select_one(selector)
        if not tag:
            continue
        src = (tag.get('data-old-hires') or tag.get('src') or '').strip()
        if src:
            return urljoin(base_url, src)
    return ''


def _extract_title_from_html(soup):
    titulo = (
        _get_meta_content(soup, 'meta[property="og:title"]')
        or _get_meta_content(soup, 'meta[name="twitter:title"]')
    )
    if titulo:
        return titulo

    for selector in ['h1[itemprop="name"]', 'h1', 'title']:
        tag = soup.select_one(selector)
        if tag:
            texto = tag.get_text(' ', strip=True)
            if texto:
                return texto
    return ''


def _get_meta_content(soup, selector):
    tag = soup.select_one(selector)
    if not tag:
        return ''
    return (tag.get('content') or '').strip()


def _formatar_preco(preco_bruto):
    preco_bruto = (preco_bruto or '').strip()
    if not preco_bruto:
        return ''

    if preco_bruto.lower().startswith('r$'):
        return preco_bruto

    match = re.search(r'(\d{1,3}(?:[\.\s]\d{3})*(?:,\d{2})|\d+(?:[\.,]\d{2})?)', preco_bruto)
    if not match:
        return preco_bruto

    valor = match.group(1).replace(' ', '')
    if ',' not in valor and '.' in valor:
        partes = valor.split('.')
        if len(partes[-1]) == 2:
            valor = ','.join(['.'.join(partes[:-1]), partes[-1]])
    return f'R$ {valor}'


def _parse_preco_to_float(preco_texto):
    texto = (preco_texto or '').strip().replace('R$', '').replace(' ', '')
    if not texto:
        return None

    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        texto = texto.replace(',', '.')

    match = re.search(r'-?\d+(?:\.\d+)?', texto)
    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def _format_preco_br(valor):
    if valor is None:
        return ''
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def parse_preco_info(preco_armazenado):
    info_padrao = {
        'preco_final': preco_armazenado,
        'preco_original': '',
        'desconto_texto': '',
        'cupom_nome': '',
    }

    if not preco_armazenado:
        return info_padrao

    try:
        data = json.loads(preco_armazenado)
    except Exception:
        return info_padrao

    if not isinstance(data, dict):
        return info_padrao

    preco_final = (data.get('preco_final') or '').strip()
    preco_original = (data.get('preco_original') or '').strip()
    desconto_texto = (data.get('desconto_texto') or '').strip()
    cupom_nome = (data.get('cupom_nome') or '').strip()

    if not preco_final:
        return info_padrao

    return {
        'preco_final': preco_final,
        'preco_original': preco_original,
        'desconto_texto': desconto_texto,
        'cupom_nome': cupom_nome,
    }


def build_preco_storage(preco_final, preco_original='', desconto_texto='', cupom_nome=''):
    payload = {
        'preco_final': (preco_final or '').strip(),
        'preco_original': (preco_original or '').strip(),
        'desconto_texto': (desconto_texto or '').strip(),
        'cupom_nome': (cupom_nome or '').strip(),
    }
    return json.dumps(payload, ensure_ascii=False)


def calcular_desconto(preco_anuncio, desconto_tipo, desconto_valor):
    preco_base = _parse_preco_to_float(preco_anuncio)
    if preco_base is None:
        return None

    try:
        valor = float(desconto_valor)
    except (TypeError, ValueError):
        return None

    if valor <= 0:
        return None

    desconto_tipo = (desconto_tipo or '').lower().strip()
    if desconto_tipo == 'percentual':
        if valor > 100:
            return None
        preco_final = preco_base * (1 - (valor / 100.0))
        desconto_texto = f"-{valor:g}%"
    elif desconto_tipo == 'fixo':
        preco_final = max(0.0, preco_base - valor)
        desconto_texto = f"- {_format_preco_br(valor)}"
    else:
        return None

    return {
        'preco_original': _format_preco_br(preco_base),
        'preco_final': _format_preco_br(preco_final),
        'desconto_texto': desconto_texto,
    }


def load_admin_coupons():
    if os.path.exists(ADMIN_COUPONS_FILE):
        try:
            with open(ADMIN_COUPONS_FILE, 'r', encoding='utf-8') as file_handle:
                data = json.load(file_handle)
            if isinstance(data, list):
                return data
        except Exception:
            return []
    return []


def save_admin_coupon(nome, desconto_tipo, desconto_valor):
    nome_limpo = (nome or '').strip().upper()
    if not nome_limpo:
        return load_admin_coupons()

    try:
        valor = float(desconto_valor)
    except (TypeError, ValueError):
        return load_admin_coupons()

    desconto_tipo = (desconto_tipo or '').strip().lower()
    if desconto_tipo not in {'percentual', 'fixo'} or valor <= 0:
        return load_admin_coupons()

    coupons = load_admin_coupons()
    coupons = [c for c in coupons if (c.get('nome') or '').upper() != nome_limpo]
    coupons.insert(0, {
        'nome': nome_limpo,
        'tipo': desconto_tipo,
        'valor': valor,
    })
    coupons = coupons[:30]

    with open(ADMIN_COUPONS_FILE, 'w', encoding='utf-8') as file_handle:
        json.dump(coupons, file_handle, ensure_ascii=False, indent=2)

    return coupons


def _extrair_do_json_ld(soup):
    titulo = ''
    preco = ''
    imagem = ''

    scripts = soup.select('script[type="application/ld+json"]')
    for script in scripts:
        conteudo = (script.string or script.get_text() or '').strip()
        if not conteudo:
            continue

        try:
            data = json.loads(conteudo)
        except Exception:
            continue

        pilha = [data]
        while pilha:
            atual = pilha.pop()
            if isinstance(atual, list):
                pilha.extend(atual)
                continue

            if not isinstance(atual, dict):
                continue

            tipo = str(atual.get('@type', '')).lower()
            if tipo == 'product' or ('product' in tipo):
                if not titulo:
                    titulo = str(atual.get('name') or '').strip()

                if not imagem:
                    img = atual.get('image')
                    if isinstance(img, list) and img:
                        imagem = str(img[0]).strip()
                    elif isinstance(img, str):
                        imagem = img.strip()

                offers = atual.get('offers')
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict) and not preco:
                    preco = str(offers.get('price') or '').strip()

            pilha.extend([v for v in atual.values() if isinstance(v, (dict, list))])

    return titulo, preco, imagem


def extrair_dados_produto(product_url):
    product_url = _normalize_url(product_url)
    if not product_url:
        raise requests.RequestException('URL inválida.')

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/126.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    final_url, html_text = _expand_short_url(product_url, headers)
    if not html_text:
        try:
            resp = requests.get(final_url, headers=headers, timeout=20)
            resp.raise_for_status()
            html_text = resp.text
        except requests.RequestException:
            html_text = ''

    soup = BeautifulSoup(html_text or '', 'lxml')

    titulo = _extract_title_from_html(soup)
    imagem = _extract_image_from_html(soup, final_url)
    preco_atual = (
        _get_meta_content(soup, 'meta[property="product:price:amount"]')
        or _get_meta_content(soup, 'meta[property="og:price:amount"]')
        or _get_meta_content(soup, 'meta[itemprop="price"]')
    )

    preco_original = (
        _get_meta_content(soup, 'meta[property="product:original_price:amount"]')
        or _get_meta_content(soup, 'meta[property="product:price:original_amount"]')
    )

    if not (titulo and imagem and preco_atual):
        jsonld_titulo, jsonld_preco, jsonld_imagem = _extrair_do_json_ld(soup)
        titulo = titulo or jsonld_titulo
        preco_atual = preco_atual or jsonld_preco
        imagem = imagem or jsonld_imagem

    prices_in_text = _extract_price_candidates(html_text)

    if not prices_in_text and final_url:
        try:
            jina_url = f"https://r.jina.ai/http://{final_url.replace('https://', '').replace('http://', '')}"
            jina_resp = requests.get(jina_url, headers=headers, timeout=20)
            if jina_resp.ok:
                prices_in_text = _extract_price_candidates(jina_resp.text)
                if not titulo:
                    title_match = re.search(r'^Title:\s*(.+)$', jina_resp.text, flags=re.MULTILINE)
                    if title_match:
                        titulo = title_match.group(1).strip()
        except requests.RequestException:
            pass

    if prices_in_text:
        if not preco_atual:
            preco_atual = _format_preco_br(prices_in_text[0])
        if not preco_original and len(prices_in_text) > 1:
            preco_original = _format_preco_br(prices_in_text[-1])

    preco_atual_fmt = _formatar_preco(preco_atual)
    preco_original_fmt = _formatar_preco(preco_original)

    if not preco_original_fmt:
        preco_original_fmt = preco_atual_fmt

    if not titulo and final_url:
        titulo = f'Oferta {extrair_loja_nome(final_url)}'

    return {
        'titulo': titulo,
        'preco': preco_atual_fmt,
        'preco_atual': preco_atual_fmt,
        'preco_original': preco_original_fmt,
        'imagem': imagem,
        'link_afiliado': final_url or product_url,
        'loja_nome': extrair_loja_nome(final_url or product_url),
        'loja_simbolo': extrair_loja_simbolo(final_url or product_url),
    }


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


def ensure_flyer_modules_or_raise_json():
    if not FLYER_MODULES_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Módulo de flyers não disponível neste deploy.'
        }), 503
    return None


def ensure_flyer_modules_or_redirect():
    if not FLYER_MODULES_AVAILABLE:
        flash('⚠️ Módulo de flyers não disponível neste deploy.', 'warning')
        return redirect(url_for('index'))
    return None


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
    try:
        return render_template('index.html', saved_coupons=saved_coupons)
    except TemplateNotFound:
        return redirect(url_for('vitrine_promocoes'))

@app.route('/calculadora-trabalhista')
def calculadora_trabalhista():
    """Página com cálculos trabalhistas"""
    try:
        return render_template('calculadora_trabalhista.html')
    except TemplateNotFound:
        return redirect(url_for('vitrine_promocoes'))

@app.route('/api/coupons')
def get_coupons():
    """API para obter cupons salvos"""
    return jsonify(load_coupons())


@app.route('/promocoes')
def vitrine_promocoes():
    promocoes = []
    for promo in buscar_promocoes_ativas():
        info = parse_preco_info(promo.preco)
        promocoes.append({
            'id': promo.id,
            'titulo': promo.titulo,
            'imagem': promo.imagem,
            'slug': promo.slug,
            'loja_nome': extrair_loja_nome(promo.link_afiliado),
            'loja_simbolo': extrair_loja_simbolo(promo.link_afiliado),
            'data_publicacao': promo.data_publicacao,
            'preco_final': info['preco_final'],
            'preco_original': info['preco_original'],
            'desconto_texto': info['desconto_texto'],
            'cupom_nome': info['cupom_nome'],
        })
    return render_template('promotions.html', promocoes=promocoes, whatsapp_group_url=WHATSAPP_GROUP_URL)


@app.route('/promocoes/<slug>')
def detalhe_promocao(slug):
    promocao = Promocao.query.filter_by(slug=slug).first_or_404()

    if promocao.expira_em < datetime.utcnow():
        abort(404)

    info = parse_preco_info(promocao.preco)
    promo_view = {
        'id': promocao.id,
        'titulo': promocao.titulo,
        'imagem': promocao.imagem,
        'slug': promocao.slug,
        'loja_nome': extrair_loja_nome(promocao.link_afiliado),
        'loja_simbolo': extrair_loja_simbolo(promocao.link_afiliado),
        'link_afiliado': promocao.link_afiliado,
        'data_publicacao': promocao.data_publicacao,
        'expira_em': promocao.expira_em,
        'preco_final': info['preco_final'],
        'preco_original': info['preco_original'],
        'desconto_texto': info['desconto_texto'],
        'cupom_nome': info['cupom_nome'],
    }
    return render_template('promotion_detail.html', promocao=promo_view, whatsapp_group_url=WHATSAPP_GROUP_URL)


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
    promocoes = []
    for promo in Promocao.query.order_by(Promocao.data_publicacao.desc()).all():
        info = parse_preco_info(promo.preco)
        promocoes.append({
            'id': promo.id,
            'titulo': promo.titulo,
            'preco_final': info['preco_final'],
            'preco_original': info['preco_original'],
            'desconto_texto': info['desconto_texto'],
            'cupom_nome': info['cupom_nome'],
            'data_publicacao': promo.data_publicacao,
            'expira_em': promo.expira_em,
            'total_cliques': promo.total_cliques,
        })
    return render_template('admin_promotions.html', promocoes=promocoes, ttl_dias=PROMOTION_TTL_DAYS)


@app.route('/api/admin/coupons', methods=['GET'])
def listar_admin_coupons():
    validar_admin_token()
    return jsonify({'ok': True, 'coupons': load_admin_coupons()})


@app.route('/api/admin/coupons', methods=['POST'])
def cadastrar_admin_coupon():
    validar_admin_token()
    payload = request.get_json(silent=True) or request.form
    nome = (payload.get('nome') or '').strip()
    desconto_tipo = (payload.get('tipo') or '').strip().lower()
    desconto_valor = (payload.get('valor') or '').strip()

    if not nome or desconto_tipo not in {'percentual', 'fixo'}:
        return jsonify({'erro': 'Informe nome e tipo válido (percentual/fixo).'}), 400

    try:
        valor = float(desconto_valor)
    except (TypeError, ValueError):
        return jsonify({'erro': 'Valor do desconto inválido.'}), 400

    if valor <= 0:
        return jsonify({'erro': 'Valor do desconto deve ser maior que zero.'}), 400

    coupons = save_admin_coupon(nome, desconto_tipo, valor)
    return jsonify({'ok': True, 'coupons': coupons})


@app.route('/api/admin/promocoes', methods=['POST'])
def criar_promocao():
    validar_admin_token()

    payload = request.get_json(silent=True) or request.form

    titulo = (payload.get('titulo') or '').strip()
    preco = (payload.get('preco') or '').strip()
    preco_anuncio = (payload.get('preco_anuncio') or '').strip()
    desconto_tipo = (payload.get('desconto_tipo') or '').strip().lower()
    desconto_valor = (payload.get('desconto_valor') or '').strip()
    cupom_nome = (payload.get('cupom_nome') or '').strip().upper()
    imagem = (payload.get('imagem') or '').strip()
    link_afiliado = (payload.get('link_afiliado') or '').strip()

    if not titulo or not preco or not imagem or not link_afiliado:
        return jsonify({'erro': 'Campos obrigatórios: titulo, preco, imagem, link_afiliado.'}), 400

    preco_original = ''
    desconto_texto = ''

    if preco_anuncio:
        preco_original = preco_anuncio

    if desconto_tipo and desconto_valor:
        calculo = calcular_desconto(preco_anuncio or preco, desconto_tipo, desconto_valor)
        if not calculo:
            return jsonify({'erro': 'Desconto inválido para o preço informado.'}), 400
        preco = calculo['preco_final']
        preco_original = calculo['preco_original']
        desconto_texto = calculo['desconto_texto']

    preco_armazenado = build_preco_storage(
        preco_final=preco,
        preco_original=preco_original,
        desconto_texto=desconto_texto,
        cupom_nome=cupom_nome,
    )

    data_publicacao = datetime.utcnow()
    promocao = Promocao(
        titulo=titulo,
        preco=preco_armazenado,
        imagem=imagem,
        link_afiliado=link_afiliado,
        slug=gerar_slug_unico(titulo),
        data_publicacao=data_publicacao,
        expira_em=data_publicacao + timedelta(days=PROMOTION_TTL_DAYS),
    )

    db.session.add(promocao)
    db.session.commit()

    return jsonify({'ok': True, 'promocao': promocao.to_dict()}), 201


@app.route('/api/admin/promocoes/extract', methods=['POST'])
def extrair_promocao_por_link():
    validar_admin_token()
    payload = request.get_json(silent=True) or request.form
    product_url = (payload.get('product_url') or payload.get('url') or '').strip()

    if not product_url:
        return jsonify({'erro': 'Campo obrigatório: product_url.'}), 400

    try:
        dados = extrair_dados_produto(product_url)
    except requests.RequestException as exc:
        return jsonify({'erro': f'Falha ao acessar URL: {exc}'}), 502

    faltantes = [
        campo for campo in ('titulo', 'preco_atual', 'imagem') if not (dados.get(campo) or '').strip()
    ]

    return jsonify({'ok': True, 'dados': dados, 'campos_faltantes': faltantes})


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
    unavailable_response = ensure_flyer_modules_or_redirect()
    if unavailable_response:
        return unavailable_response

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
    unavailable_response = ensure_flyer_modules_or_raise_json()
    if unavailable_response:
        return unavailable_response

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
    unavailable_response = ensure_flyer_modules_or_redirect()
    if unavailable_response:
        return unavailable_response

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
    unavailable_response = ensure_flyer_modules_or_redirect()
    if unavailable_response:
        return unavailable_response

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
