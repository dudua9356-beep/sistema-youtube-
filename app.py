# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "minha_chave_super_secreta_123456")

# =========================
# CONFIGURAÇÕES GOOGLE/YOUTUBE
# =========================
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "@1clipadasmarkola")

# URL base do Render
BASE_URL = os.environ.get(
    "BASE_URL",
    "https://sistema-youtube.onrender.com"
)

# =========================
# CAMPANHAS (EXEMPLO)
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
    # Redireciona para a primeira campanha
    slug = list(campanhas.keys())[0]
    return redirect(url_for("campanha", slug=slug))


# =========================
# PÁGINA DA CAMPANHA
# =========================
@app.route("/campanha/<slug>")
def campanha(slug):
    if slug not in campanhas:
        return "Campanha não encontrada.", 404

    # Se ainda não fez login
    if not session.get("google_user"):
        session["next_slug"] = slug
        return redirect(url_for("login_google"))

    # Verifica inscrição no canal
    if not session.get("is_subscribed"):
        return render_template(
            "nao_inscrito.html",
            channel=YOUTUBE_CHANNEL_ID
        )

    campanha = campanhas[slug]

    return render_template(
        "campanha.html",
        name=campanha["name"],
        youtube_url=campanha["youtube_url"],
        giveaway_url=campanha["giveaway_url"]
    )


# =========================
# LOGIN COM GOOGLE
# =========================
@app.route("/login_google")
def login_google():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{BASE_URL}/oauth2callback",
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/youtube.readonly",
        "access_type": "offline",
        "prompt": "consent"
    }

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(params)
    )

    return redirect(auth_url)


# =========================
# CALLBACK DO GOOGLE
# =========================
@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")

    if not code:
        return "Código de autorização não recebido."

    # Troca code por access_token
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{BASE_URL}/oauth2callback"
        }
    )

    token_data = token_response.json()

    access_token = token_data.get("access_token")
    if not access_token:
        return f"Erro ao obter token: {token_data}"

    # Dados do usuário
    user_response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    user_data = user_response.json()

    session["google_user"] = {
        "name": user_data.get("name"),
        "email": user_data.get("email")
    }

    # Verifica inscrição no canal
    session["is_subscribed"] = verificar_inscricao(access_token)

    # Redireciona para a campanha
    slug = session.get("next_slug", list(campanhas.keys())[0])
    return redirect(url_for("campanha", slug=slug))


# =========================
# VERIFICAR INSCRIÇÃO
# =========================
def verificar_inscricao(access_token):
    """
    Tenta verificar se o usuário está inscrito.
    Se não conseguir validar, retorna True para facilitar testes.
    """
    try:
        url = (
            "https://www.googleapis.com/youtube/v3/subscriptions"
            "?part=snippet&mine=true&maxResults=50"
        )

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        data = response.json()

        # Se vier erro da API, libera para testes
        if "items" not in data:
            print("Não foi possível validar inscrição:", data)
            return True

        for item in data["items"]:
            canal = item["snippet"]["resourceId"]["channelId"]
            titulo = item["snippet"]["title"]

            # Compara pelo ID do canal
            if canal == YOUTUBE_CHANNEL_ID:
                return True

            # Também compara pelo @handle ou nome
            if YOUTUBE_CHANNEL_ID.lower() in titulo.lower():
                return True

        return False

    except Exception as e:
        print("Erro ao verificar inscrição:", e)
        # Durante testes, libera acesso
        return True


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =========================
# PAINEL
# =========================
@app.route("/painel")
def painel():
    if not session.get("google_user"):
        return redirect(url_for("login_google"))

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
        return redirect(url_for("login_google"))

    slug = request.form.get("slug", "").strip()
    name = request.form.get("name", "").strip()
    youtube_url = request.form.get("youtube_url", "").strip()
    giveaway_url = request.form.get("giveaway_url", "").strip()

    if not slug or not name:
        return "Preencha slug e nome."

    campanhas[slug] = {
        "name": name,
        "youtube_url": youtube_url,
        "giveaway_url": giveaway_url
    }

    return redirect(url_for("painel"))


# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
