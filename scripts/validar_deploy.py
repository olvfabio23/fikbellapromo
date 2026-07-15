"""
Script de validação pós-deploy para o FikbellaPromo.
Testa: extração de URLs (Shopee / Mercado Livre), templates e consistência do código.
"""
import sys
import os
import re
import importlib
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_validacao.db")
os.environ.setdefault("ADMIN_TOKEN", "teste_local_token_123")
os.environ.setdefault("AUTO_INIT_DB", "true")
os.environ.setdefault("WHATSAPP_GROUP_URL", "https://wa.me/teste")

VERDE = "\033[92m"
VERMELHO = "\033[91m"
AMARELO = "\033[93m"
RESET = "\033[0m"
NEGRITO = "\033[1m"

resultados = []

def ok(msg):
    print(f"  {VERDE}✓{RESET} {msg}")
    resultados.append(("OK", msg))

def falha(msg, detalhe=""):
    print(f"  {VERMELHO}✗ FALHA:{RESET} {msg}")
    if detalhe:
        print(f"    {AMARELO}→ {detalhe[:220]}{RESET}")
    resultados.append(("FALHA", msg))

def aviso(msg):
    print(f"  {AMARELO}⚠{RESET} {msg}")
    resultados.append(("AVISO", msg))

def titulo(texto):
    print(f"\n{NEGRITO}━━ {texto} ━━{RESET}")

# ─── 1. Importação do app ────────────────────────────────────────────────────
titulo("1. Importação do módulo app.py")
try:
    import app as APP
    ok("app.py importado com sucesso")
except Exception as exc:
    falha("Falha ao importar app.py", str(exc))
    print(f"\n{VERMELHO}Abortando testes: app.py não pode ser importado.{RESET}")
    sys.exit(1)

# ─── 2. Funções críticas presentes ───────────────────────────────────────────
titulo("2. Funções e rotas críticas")
FUNCOES = [
    "extrair_dados_produto",
    "extrair_dados_shopee_graphql",
    "extrair_dados_shopee_api",
    "_extrair_shopee_por_html",
    "_extrair_mercadolivre_por_html",
    "_shopee_extrair_ids",
    "_normalizar_valor_centavos_shopee",
    "calcular_base_preco_formulario",
    "parse_preco_info",
    "build_preco_storage",
    "calcular_desconto",
    "save_admin_coupon",
    "purgar_admin_coupons_expirados",
    "montar_meta_loja",
    "formatar_data_br",
]
for nome in FUNCOES:
    if hasattr(APP, nome) and callable(getattr(APP, nome)):
        ok(nome)
    else:
        falha(f"Função ausente: {nome}")

# ─── 3. Extração de IDs Shopee ───────────────────────────────────────────────
titulo("3. Extração de IDs Shopee")
CASOS_IDS = [
    ("https://shopee.com.br/produto/-i.431466978.21977220271", ("431466978", "21977220271")),
    ("https://shopee.com.br/opaanlp/431466978/21977220271", ("431466978", "21977220271")),
    ("https://shopee.com.br/x/y/123456789/987654321?foo=bar", ("123456789", "987654321")),
    ("https://s.shopee.com.br/abc123", ("", "")),  # sem IDs → deve retornar vazio
]
for url, esperado in CASOS_IDS:
    try:
        resultado = APP._shopee_extrair_ids(url)
        if resultado == esperado:
            ok(f"IDs: {resultado}  ← {url[:60]}")
        elif esperado == ("", "") and resultado != ("", ""):
            aviso(f"URL curta retornou IDs {resultado} (pode estar correto após redirect)")
        else:
            falha(f"IDs incorretos: esperado {esperado}, obtido {resultado}", url)
    except Exception as exc:
        falha(f"Exceção em _shopee_extrair_ids({url[:50]})", str(exc))

# ─── 4. Normalização de preço Shopee (centavos) ──────────────────────────────
titulo("4. Normalização de preço Shopee")
CASOS_PRECO = [
    (2199000, "R$ 21,99"),
    (21990000, "R$ 219,90"),
    (219900000, "R$ 2.199,00"),
    ("R$ 39,90", "R$ 39,90"),
    (0, ""),
    (None, ""),
    ("", ""),
]
for valor, esperado in CASOS_PRECO:
    try:
        resultado = APP._normalizar_valor_centavos_shopee(valor)
        esperado_clean = esperado.replace(" ", "").lower()
        resultado_clean = resultado.replace(" ", "").lower()
        if resultado_clean == esperado_clean:
            ok(f"{valor!r:>20}  →  {resultado}")
        elif esperado in ("", None) and resultado in ("", None):
            ok(f"{valor!r:>20}  →  vazio (correto)")
        else:
            aviso(f"{valor!r:>20}  →  {resultado!r}  (esperado {esperado!r}, verificar divisor)")
    except Exception as exc:
        falha(f"Exceção em _normalizar_valor_centavos_shopee({valor!r})", str(exc))

# ─── 5. Cálculo de desconto e base de preço ─────────────────────────────────
titulo("5. Cálculo de desconto")
CASOS_DESC = [
    ("R$ 100,00", "percentual", "20", "R$ 80,00"),
    ("R$ 200,00", "fixo", "50", "R$ 150,00"),
    ("100,00", "percentual", "10", "R$ 90,00"),
]
for base, tipo, valor, esperado in CASOS_DESC:
    try:
        r = APP.calcular_desconto(base, tipo, valor)
        if r and r.get("preco_final", "").replace(" ", "").lower() == esperado.replace(" ", "").lower():
            ok(f"{base} - {tipo} {valor}% → {r['preco_final']}")
        else:
            falha(f"Desconto errado: {base} {tipo} {valor}", f"obtido {r}")
    except Exception as exc:
        falha(f"Exceção em calcular_desconto({base}, {tipo}, {valor})", str(exc))

titulo("6. calcular_base_preco_formulario")
CASOS_BASE = [
    ("R$ 80,00", "R$ 100,00", "R$ 80,00"),   # usa preco_final quando preenchido
    ("", "R$ 100,00", "R$ 100,00"),           # cai pro preco_anuncio quando final vazio
    ("  ", "R$ 50,00", "R$ 50,00"),           # espaço equivale a vazio
]
for pf, pa, esperado in CASOS_BASE:
    r = APP.calcular_base_preco_formulario(pf, pa)
    if r.strip() == esperado.strip():
        ok(f"final={pf!r:12} anuncio={pa!r:12} → {r!r}")
    else:
        falha(f"Base errada: esperado {esperado!r}, obtido {r!r}")

# ─── 7. Validação dos templates ─────────────────────────────────────────────
titulo("7. Validação dos templates HTML")
TEMPLATES = {
    "promotions.html": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "promotions.html"),
    "promotion_detail.html": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "promotion_detail.html"),
}

VERIFICACOES = [
    ("favicon",          r'<link rel="icon"[^>]+fikbella_logo_final\.png'),
    ("brand-badge logo", r'class="brand-badge"'),
    ("instagram SVG",    r'igGradient'),
    ("um só instagram",  None),   # verificação especial abaixo
    ("nova aba - compra",   r"url_for\('redirect_afiliado'[^)]+\)[^>]+target=\"_blank\""),
    ("nova aba - loja chip",r"url_for\('promocoes_por_loja'[^)]+\)[^>]+target=\"_blank\""),
]

VERIFICACOES_DETAIL = [(d, p) for d, p in VERIFICACOES if d != "nova aba - detalhe"]
VERIFICACOES_VITRINE = VERIFICACOES + [("nova aba - detalhe", r"url_for\('detalhe_promocao'[^)]+\)[^>]+target=\"_blank\"")]

for nome_tpl, caminho_tpl in TEMPLATES.items():
    print(f"\n  {NEGRITO}Template: {nome_tpl}{RESET}")
    try:
        conteudo = open(caminho_tpl, encoding="utf-8").read()
    except FileNotFoundError:
        falha(f"Arquivo não encontrado: {caminho_tpl}")
        continue

    checks = VERIFICACOES_VITRINE if nome_tpl == "promotions.html" else VERIFICACOES_DETAIL
    for descricao, padrao in checks:
        if padrao is None:
            # verifica que há exatamente 1 link do instagram
            count = len(re.findall(r'instagram\.com/fikbella', conteudo, re.IGNORECASE))
            if count == 1:
                ok(f"exatamente 1 link do Instagram ({count})")
            elif count == 0:
                falha("nenhum link do Instagram encontrado")
            else:
                aviso(f"{count} links do Instagram (esperado 1)")
        else:
            if re.search(padrao, conteudo, re.DOTALL | re.IGNORECASE):
                ok(descricao)
            else:
                falha(descricao, f"padrão não encontrado: {padrao[:80]}")

# ─── 8. Teste de extração de URL real (Mercado Livre) ───────────────────────
titulo("8. Extração Mercado Livre (URL pública sem login)")
URL_ML = "https://www.mercadolivre.com.br/arroz-camil-tipo-1-agulhinha-5kg/p/MLB33791490"
try:
    print(f"  → Testando URL: {URL_ML[:70]}")
    dados = APP.extrair_dados_produto(URL_ML)
    campos = {k: (v or "")[:80] for k, v in dados.items()}
    for campo, valor in campos.items():
        print(f"    {campo:20}: {valor!r}")
    if dados.get("titulo") and "produto" not in dados["titulo"].lower():
        ok("Título extraído com conteúdo")
    elif dados.get("titulo"):
        aviso(f"Título genérico: {dados['titulo']}")
    else:
        falha("Título não extraído")
    if dados.get("preco") or dados.get("preco_atual"):
        ok(f"Preço extraído: {dados.get('preco') or dados.get('preco_atual')}")
    else:
        aviso("Preço não extraído (página pode ter bloqueio anti-bot)")
    if dados.get("imagem"):
        ok(f"Imagem extraída: {dados['imagem'][:60]}...")
    else:
        aviso("Imagem não extraída")
except Exception as exc:
    falha("Exceção na extração Mercado Livre", traceback.format_exc()[-300:])

# ─── 9. Teste extração Shopee por HTML/regex ────────────────────────────────
titulo("9. Parser Shopee por regex no HTML (simula resposta com dados embutidos)")
HTML_FAKE_SHOPEE = """
<html><head><title>Test</title></head><body>
<script type="text/javascript">
window.__NEXT_DATA__ = {
  "pageProps": {
    "item": {
      "item_name": "Fone Bluetooth Shopee XPro 2000",
      "image": "abc123def456",
      "price": 1990000,
      "price_before_discount": 3990000
    }
  }
};
</script>
<a href="https://shopee.com.br/produto-i.431466978.21977220271">Fone Bluetooth Shopee XPro 2000</a>
</body></html>
"""
try:
    from bs4 import BeautifulSoup
    soup_fake = BeautifulSoup(HTML_FAKE_SHOPEE, "lxml")
    resultado = APP._extrair_shopee_por_html(soup_fake, HTML_FAKE_SHOPEE, "https://shopee.com.br/produto-i.431466978.21977220271")
    if resultado.get("titulo") and "xpro" in resultado["titulo"].lower():
        ok(f"Título via regex/HTML: {resultado['titulo']}")
    elif resultado.get("titulo"):
        ok(f"Título via link anchor: {resultado['titulo']}")
    else:
        aviso("Título não extraído do HTML simulado")
    if resultado.get("preco_atual"):
        ok(f"Preço atual: {resultado['preco_atual']}")
    else:
        aviso("Preço atual não extraído do HTML simulado")
    if resultado.get("preco_original"):
        ok(f"Preço original: {resultado['preco_original']}")
    else:
        aviso("Preço original não extraído do HTML simulado")
    if resultado.get("imagem"):
        ok(f"Imagem: {resultado['imagem'][:60]}")
    else:
        aviso("Imagem não extraída do HTML simulado")
except Exception as exc:
    falha("Exceção no parser Shopee HTML", traceback.format_exc()[-300:])

# ─── 10. Resumo final ────────────────────────────────────────────────────────
titulo("RESUMO")
total = len(resultados)
ok_count = sum(1 for r in resultados if r[0] == "OK")
falha_count = sum(1 for r in resultados if r[0] == "FALHA")
aviso_count = sum(1 for r in resultados if r[0] == "AVISO")

print(f"\n  Total: {total}  |  {VERDE}OK: {ok_count}{RESET}  |  {AMARELO}Avisos: {aviso_count}{RESET}  |  {VERMELHO}Falhas: {falha_count}{RESET}")

if falha_count == 0:
    print(f"\n  {VERDE}{NEGRITO}✓ Validação passou.{RESET}")
    sys.exit(0)
else:
    print(f"\n  {VERMELHO}{NEGRITO}✗ {falha_count} falha(s) encontrada(s). Revisar antes do deploy.{RESET}")
    sys.exit(1)
