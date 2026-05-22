from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "minha_chave_super_secreta_123456"
)

app.permanent_session_lifetime = timedelta(days=1)

# =========================
# CONFIGURAÇÕES
# =========================
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

BASE_URL = os.environ.get(
    "BASE_URL",
    "https://sistema-youtube.onrender.com"
)

# =========================
# LOGIN STREAMER
# =========================
STREAMER_USER = os.environ.get(
    "STREAMER_USER",
    "admin"
)

STREAMER_PASSWORD = os.environ.get(
    "STREAMER_PASSWORD",
    "Omarkola@321"
)

# =========================
# CAMPANHAS
# =========================
campanhas = {
    "money-bum": {
        "name": "Money Bum",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "giveaway_url": "https://google.com",
        "created_at": datetime.now()
    }
}


# =========================
# LIMPAR CAMPANHAS
# =========================
def limpar_campanhas():

    agora = datetime.now()

    expiradas = []

    for slug, dados in campanhas.items():

        criado = dados.get("created_at")

        if criado:

            diferenca = agora - criado

            if diferenca > timedelta(hours=24):

                expiradas.append(slug)

    for slug in expiradas:

        del campanhas[slug]


# =========================
# HOME
# =========================
@app.route("/")
def home():

    if session.get("streamer_logado"):

        return redirect(url_for("painel"))

    return render_template("login.html")


# =========================
# LOGIN GOOGLE
# =========================
@app.route("/login_google")
def login_google():

    slug = request.args.get("slug")

    if slug:
        session["next_slug"] = slug

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:

        return (
            "Configure GOOGLE_CLIENT_ID e "
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
        return "Código não recebido."

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

    user_response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        timeout=30
    )

    user_data = user_response.json()

    session.permanent = True

    session["google_user"] = {
        "name": user_data.get("name", "Usuário"),
        "email": user_data.get("email", "")
    }

    session["is_subscribed"] = True

    next_slug = session.pop("next_slug", None)

    if next_slug:

        return redirect(
            url_for(
                "campanha",
                slug=next_slug
            )
        )

    if session.get("streamer_logado"):

        return redirect(url_for("painel"))

    return redirect(url_for("home"))


# =========================
# LOGIN PAINEL
# =========================
@app.route("/painel_login", methods=["GET", "POST"])
def painel_login():

    erro = None

    if request.method == "POST":

        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if (
            usuario == STREAMER_USER
            and senha == STREAMER_PASSWORD
        ):

            session["streamer_logado"] = True

            return redirect(url_for("painel"))

        else:

            erro = "Login inválido"

    return render_template(
        "painel_login.html",
        erro=erro
    )


# =========================
# PAINEL
# =========================
@app.route("/painel")
def painel():

    limpar_campanhas()

    if not session.get("streamer_logado"):

        return redirect(url_for("painel_login"))

    return render_template(
        "painel.html",
        campanhas=campanhas
    )


# =========================
# CRIAR CAMPANHA
# =========================
@app.route("/criar", methods=["POST"])
def criar():

    if not session.get("streamer_logado"):

        return redirect(url_for("painel_login"))

    slug = request.form.get("slug", "").strip()
    name = request.form.get("name", "").strip()
    youtube_url = request.form.get("youtube_url", "").strip()
    giveaway_url = request.form.get("giveaway_url", "").strip()

    if (
        not slug
        or not name
        or not youtube_url
        or not giveaway_url
    ):

        return "Preencha todos os campos."

    campanhas[slug] = {
        "name": name,
        "youtube_url": youtube_url,
        "giveaway_url": giveaway_url,
        "created_at": datetime.now()
    }

    return redirect(url_for("painel"))


# =========================
# CAMPANHA
# =========================
@app.route("/campanha/<slug>")
def campanha(slug):

    limpar_campanhas()

    if slug not in campanhas:

        return "Campanha não encontrada.", 404

    if not session.get("google_user"):

        return redirect(
            f"/login_google?slug={slug}"
        )

    dados = campanhas[slug]

    return render_template(
        "campanha.html",
        slug=slug,
        name=dados["name"],
        youtube_url=dados["youtube_url"]
    )


# =========================
# VERIFICADO
# =========================
@app.route("/campanha/<slug>/verificado")
def marcar_verificado(slug):

    limpar_campanhas()

    if slug not in campanhas:

        return "Campanha não encontrada.", 404

    if not session.get("google_user"):

        return redirect(
            f"/login_google?slug={slug}"
        )

    session[f"acesso_{slug}"] = True

    return "ok"


# =========================
# LIBERAR SORTEIO
# =========================
@app.route("/campanha/<slug>/liberar")
def liberar_sorteio(slug):

    limpar_campanhas()

    if slug not in campanhas:

        return "Campanha não encontrada.", 404

    if not session.get("google_user"):

        return redirect(
            f"/login_google?slug={slug}"
        )

    acesso = session.get(f"acesso_{slug}")

    if not acesso:

        return redirect(
            url_for(
                "campanha",
                slug=slug
            )
        )

    session.pop(f"acesso_{slug}", None)

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

    return redirect(url_for("painel_login"))


# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
