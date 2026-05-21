from flask import Flask, redirect, url_for, session, render_template
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_super_secreta")

# Campanhas de exemplo
campanhas = {
    "money-bum": {
        "name": "Money Bum",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "giveaway_url": "https://google.com"
    }
}


@app.route("/")
def home():
    if session.get("google_user"):
        return redirect(url_for("painel"))
    return render_template("login.html")


@app.route("/login_google")
def login_google():
    # Login simplificado apenas para teste
    session["google_user"] = {
        "name": "Administrador",
        "email": "admin@sistema.com"
    }
    session["is_subscribed"] = True
    return redirect(url_for("painel"))


@app.route("/painel")
def painel():
    if not session.get("google_user"):
        return redirect(url_for("home"))

    return render_template(
        "painel.html",
        campanhas=campanhas,
        usuario=session["google_user"]
    )


@app.route("/campanha/<slug>")
def campanha(slug):
    if slug not in campanhas:
        return "Campanha não encontrada.", 404

    if not session.get("google_user"):
        session["next_slug"] = slug
        return redirect(url_for("home"))

    dados = campanhas[slug]

    return render_template(
        "campanha.html",
        name=dados["name"],
        youtube_url=dados["youtube_url"],
        giveaway_url=dados["giveaway_url"]
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
