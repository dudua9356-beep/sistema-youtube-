from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
import secrets

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "database.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            youtube_url TEXT,
            giveaway_url TEXT,
            token TEXT UNIQUE
        )
    """)

    # cria usuário admin padrão
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", "123456")
        )

    conn.commit()
    conn.close()

@app.before_request
def setup():
    init_db()

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/painel")
        else:
            erro = "Usuário ou senha inválidos."

    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/painel", methods=["GET", "POST"])
def painel():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        youtube_url = request.form["youtube_url"]
        giveaway_url = request.form["giveaway_url"]
        token = secrets.token_urlsafe(8)

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO campaigns (name, youtube_url, giveaway_url, token)
            VALUES (?, ?, ?, ?)
        """, (name, youtube_url, giveaway_url, token))
        conn.commit()
        conn.close()

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, token FROM campaigns ORDER BY id DESC")
    campaigns = c.fetchall()
    conn.close()

    return render_template("painel.html", campaigns=campaigns)

@app.route("/campanha/<token>", methods=["GET", "POST"])
def campanha(token):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT name, youtube_url, giveaway_url
        FROM campaigns
        WHERE token=?
    """, (token,))
    campaign = c.fetchone()
    conn.close()

    if not campaign:
        return "Campanha não encontrada."

    name, youtube_url, giveaway_url = campaign

    liberar = False
    if request.method == "POST":
        liberar = True

    return render_template(
        "campanha.html",
        name=name,
        youtube_url=youtube_url,
        giveaway_url=giveaway_url,
        liberar=liberar
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
