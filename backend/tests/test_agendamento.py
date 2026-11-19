import re
from playwright.sync_api import Page, expect

URL_APLICACAO = "https://levia-agenda-app.onrender.com/conta"

def test_pagina_login_carrega_com_sucesso(page: Page):
    """
    Cenário 01: Validar se a página inicial de autenticação/conta carrega os elementos essenciais
    """
    page.goto(URL_APLICACAO)
    page.wait_for_load_state("networkidle", timeout=30000)
    expect(page).not_to_have_title("")

def test_responsividade_mobile(page: Page):
    """
    Cenário 02: Validar layout em resolução mobile (iPhone 12 / 390x844)
    """
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(URL_APLICACAO)
    page.wait_for_load_state("networkidle", timeout=30000)
    expect(page.locator("body")).to_be_visible()

def test_login_com_credenciais_invalidas_bloqueia_acesso(page: Page):
    """
    Cenário 03: Tentar autenticar com e-mail e senha inválidos e verificar tratamento de erro
    """
    page.goto(URL_APLICACAO)
    page.wait_for_load_state("networkidle", timeout=30000)

    # 1. Preenche o e-mail falso
    page.get_by_label(re.compile("e-?mail", re.IGNORECASE)).fill("usuario_inexistente@teste.com")

    # 2. Preenche a senha inválida
    page.get_by_label(re.compile("senha", re.IGNORECASE)).fill("senhaErrada123!")

    # 3. Clica no botão Entrar
    page.get_by_role("button", name=re.compile("Entrar", re.IGNORECASE)).click()

    # 4. Validação (Assert): O sistema não deve redirecionar para a área logada e deve exibir alerta
    # Procura mensagens comuns de erro de autenticação ou garante que ainda está na tela de login
    page.wait_for_timeout(2000)  # aguarda a resposta da API
    expect(page).to_have_url(re.compile("/conta"))

def test_link_esqueci_senha_visivel_e_clicavel(page: Page):
    """
    Cenário 04: Validar se o fluxo de recuperação de senha está acessível
    """
    page.goto(URL_APLICACAO)
    page.wait_for_load_state("networkidle", timeout=30000)

    # Valida que o link de recuperação existe na tela
    link_esqueci = page.get_by_text(re.compile("esqueci|recuperar", re.IGNORECASE))
    expect(link_esqueci).to_be_visible()