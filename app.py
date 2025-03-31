
from flask import Flask, request, render_template, redirect, url_for, session
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'chave-secreta'

# === Banco de Dados ===
def init_db():
    conn = sqlite3.connect('agendamentos.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            horario TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensagens (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')

    mensagens_padrao = {
        'horario': 'Segunda a Sexta, das 9h às 18h.',
        'cardapio': '1. Pizza - R$ 25\n2. Burger - R$ 20\n3. Refri - R$ 5'
    }

    for chave, valor in mensagens_padrao.items():
        cursor.execute('INSERT OR IGNORE INTO mensagens (chave, valor) VALUES (?, ?)', (chave, valor))

    conn.commit()
    conn.close()

init_db()

# === WhatsApp Bot ===
@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    msg = request.form.get('Body').strip().lower()
    resp = MessagingResponse()
    resposta = resp.message()

    conn = sqlite3.connect('agendamentos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM mensagens WHERE chave = 'horario'")
    horario = cursor.fetchone()[0]
    cursor.execute("SELECT valor FROM mensagens WHERE chave = 'cardapio'")
    cardapio = cursor.fetchone()[0]

    if msg in ['oi', 'olá', 'menu']:
        resposta.body("Olá! 👋 Bem-vindo! Digite:\n\n1️⃣ Horário\n2️⃣ Cardápio\n3️⃣ Agendar")
    elif msg == '1':
        resposta.body(f"Nosso horário de atendimento é:\n{horario}")
    elif msg == '2':
        resposta.body(f"Aqui está o cardápio:\n🍕🍔🥤\n{cardapio}")
    elif msg == '3':
        resposta.body("Ótimo! Qual o seu nome?")
        session['agendamento'] = 'nome'
    elif msg == 'ver agendamentos' and request.form.get('From') == 'whatsapp:+seu_numero_aqui':
        cursor.execute('SELECT nome, horario FROM agendamentos')
        agendamentos = cursor.fetchall()
        if agendamentos:
            texto = "\n".join([f"{nome} - {hora}" for nome, hora in agendamentos])
        else:
            texto = "Nenhum agendamento encontrado."
        resposta.body(f"📋 Agendamentos:\n{texto}")
    elif 'agendamento' in session:
        etapa = session['agendamento']
        if etapa == 'nome':
            session['nome'] = msg
            session['agendamento'] = 'horario'
            resposta.body("Qual horário deseja agendar?")
        elif etapa == 'horario':
            nome = session.pop('nome')
            horario = msg
            cursor.execute('INSERT INTO agendamentos (nome, horario) VALUES (?, ?)', (nome, horario))
            conn.commit()
            session.pop('agendamento')
            resposta.body(f"✅ Agendamento confirmado para {nome} às {horario}")
    else:
        resposta.body("Desculpe, não entendi. Digite 'oi' para começar.")

    conn.close()
    return str(resp)

# === Painel Web ===
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]
        if email == "admin@bot.com" and senha == "1234":
            session["usuario"] = email
            return redirect(url_for("painel"))
    return render_template("login.html")

@app.route("/painel")
def painel():
    if "usuario" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect('agendamentos.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nome, horario FROM agendamentos')
    agendamentos = cursor.fetchall()
    conn.close()
    return render_template("painel.html", agendamentos=agendamentos)

@app.route("/editar", methods=["GET", "POST"])
def editar():
    if "usuario" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect('agendamentos.db')
    cursor = conn.cursor()
    if request.method == "POST":
        novo_horario = request.form["horario"]
        novo_cardapio = request.form["cardapio"]
        cursor.execute("UPDATE mensagens SET valor = ? WHERE chave = 'horario'", (novo_horario,))
        cursor.execute("UPDATE mensagens SET valor = ? WHERE chave = 'cardapio'", (novo_cardapio,))
        conn.commit()
        return redirect(url_for("painel"))
    cursor.execute("SELECT chave, valor FROM mensagens")
    mensagens = dict(cursor.fetchall())
    conn.close()
    return render_template("editar.html", horario=mensagens.get("horario"), cardapio=mensagens.get("cardapio"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# === Início da aplicação (com suporte ao Render) ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
