from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "minha_chave_super_secreta_123456")

# =========================
# CONFIGURAÇÕES
# =========================
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "@1clipadasmarkola")
BASE_URL = os.environ.get("BASE_URL", "https://sistema-youtube.onrender.com")

# =========================
# CAMPANHAS (em memória)
# =========================
campanhas = {
    "money-bum": {
        "name": "Money Bum",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "giveaway_url": "https://google.com"
    }
}


# =========================
# HOME
# =========================
@app.route("/")
def home():
    # Se já estiver logado, abre direto o painel
    if session.get("google_user"):
        return redirect(url_for("painel"))

    # Caso contrário, mostra a tela de login
    return render_template("login.html")


# =========================
# LOGIN COM GOOGLE
# =========================
@app.route("/login_google")
def login_google():
    # Verifica se as variáveis estão configuradas
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return (
            "Configure as variáveis GOOGLE_CLIENT_ID e "
            "GOOGLE_CLIENT_SECRET no Render."
        )

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{BASE_URL}/oauth2callback",
        "response_type": "code",
        "scope": (
            "openid email profile "
            "https://www.googleapis.com/auth/youtube.readonly"
        ),
        "access_type": "offline",
        "prompt": "consent"
    }

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(params)
    )

    return redirect(auth_url)


# =========================
# CALLBACK GOOGLE
# =========================
@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")

    if not code:
        return "Código de autorização não recebido."

    # Troca o code por access token
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{BASE_URL}/oauth2callback"
        },
        timeout=30
    )

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return f"Erro ao obter token: {token_data}"

    # Busca informações do usuário
    user_response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        timeout=30
    )

    user_data = user_response.json()

    # Salva dados do usuário na sessão
    session["google_user"] = {
        "name": user_data.get("name", "Usuário"),
        "email": user_data.get("email", "")
    }

    # Aqui você pode colocar verificação real de inscrição
    # Por enquanto, libera automaticamente
    session["is_subscribed"] = True

    # Se veio de uma campanha, volta para ela
    next_slug = session.pop("next_slug", None)
    if next_slug:
        return redirect(url_for("campanha", slug=next_slug))

    # Caso contrário, vai para o painel
    return redirect(url_for("painel"))


# =========================
# PAINEL
# =========================
@app.route("/painel")
def painel():
    if not session.get("google_user"):
        return redirect(url_for("home"))

    return render_template(
        "painel.html",
        campanhas=campanhas,
        usuario=session["google_user"]
    )


# =========================
# CRIAR CAMPANHA
# =========================
@app.route("/criar", methods=["POST"])
def criar():
    if not session.get("google_user"):
        return redirect(url_for("home"))

    slug = request.form.get("slug", "").strip()
    name = request.form.get("name", "").strip()
    youtube_url = request.form.get("youtube_url", "").strip()
    giveaway_url = request.form.get("giveaway_url", "").strip()

    if not slug or not name or not youtube_url or not giveaway_url:
        return "Preencha todos os campos."

    campanhas[slug] = {
        "name": name,
        "youtube_url": youtube_url,
        "giveaway_url": giveaway_url
    }

    return redirect(url_for("painel"))


# =========================
# CAMPANHA
# =========================
@app.route("/campanha/<slug>")
def campanha(slug):
    if slug not in campanhas:
        return "Campanha não encontrada.", 404

    # Se não estiver logado, salva a campanha e pede login
    if not session.get("google_user"):
        session["next_slug"] = slug
        return redirect(url_for("home"))

    # Se quiser exigir inscrição, descomente:
    # if not session.get("is_subscribed"):
    #     return "Você precisa estar inscrito no canal."

    dados = campanhas[slug]

    # Não enviamos giveaway_url para o HTML
    # para evitar que o link real apareça no código-fonte.
    return render_template(
        "campanha.html",
        name=dados["name"],
        youtube_url=dados["youtube_url"]
    )


# =========================
# LIBERAR SORTEIO (PROTEGIDO)
# =========================
@app.route("/campanha/<slug>/liberar")
def liberar_sorteio(slug):

    if slug not in campanhas:
        return "Campanha não encontrada.", 404

    if not session.get("google_user"):
        return redirect(url_for("home"))

    dados = campanhas[slug]

    return render_template(
        "sorteio.html",
        name=dados["name"],
        giveaway_url=dados["giveaway_url"]
    )


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =========================
# EXECUÇÃO LOCAL
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
