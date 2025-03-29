
from flask import Flask, request, redirect, render_template, session, url_for
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3

app = Flask(__name__)
app.secret_key = 'segredo123'  # Troque por algo seguro

# Config inicial
ADMIN_EMAIL = 'admin@bot.com'
ADMIN_SENHA = '1234'

# Banco de dados
def init_db():
    conn = sqlite3.connect('agendamentos.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefone TEXT,
            nome TEXT,
            horario TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS mensagens (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')
    conn.commit()

    # Mensagens padrão
    defaults = {
        'horario': 'Segunda a Sexta, das 9h às 18h.',
        'cardapio': '1. Pizza - R$ 25\n2. Burger - R$ 20\n3. Refri - R$ 5'
    }

    for chave, valor in defaults.items():
        c.execute("INSERT OR IGNORE INTO mensagens (chave, valor) VALUES (?, ?)", (chave, valor))

    conn.commit()
    conn.close()

init_db()
agendamento_temp = {}

# ---------------------- ROTAS WHATSAPP ----------------------

@app.route("/whatsapp", methods=["POST"])
def reply_whatsapp():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    # Ver mensagens personalizadas
    conn = sqlite3.connect("agendamentos.db")
    c = conn.cursor()
    c.execute("SELECT chave, valor FROM mensagens")
    mensagens_dict = dict(c.fetchall())
    conn.close()

    # Comando do dono para ver agendamentos
    if incoming_msg == "ver agendamentos" and from_number == "whatsapp:+5511999999999":
        conn = sqlite3.connect("agendamentos.db")
        c = conn.cursor()
        c.execute("SELECT nome, horario FROM agendamentos ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        if rows:
            resposta = "*Agendamentos:*\n" + "\n".join(["- {}, {}".format(nome, horario) for nome, horario in rows])
        else:
            resposta = "Nenhum agendamento encontrado."
        msg.body(resposta)
        return str(resp)

    # Etapas de agendamento
    if from_number in agendamento_temp:
        etapa = agendamento_temp[from_number]["etapa"]

        if etapa == 1:
            agendamento_temp[from_number]["nome"] = incoming_msg
            agendamento_temp[from_number]["etapa"] = 2
            msg.body("Ótimo! Agora diga o horário desejado (ex: amanhã às 14h).")
        elif etapa == 2:
            nome = agendamento_temp[from_number]["nome"]
            horario = incoming_msg

            conn = sqlite3.connect("agendamentos.db")
            c = conn.cursor()
            c.execute("INSERT INTO agendamentos (telefone, nome, horario) VALUES (?, ?, ?)",
                      (from_number, nome, horario))
            conn.commit()
            conn.close()

            del agendamento_temp[from_number]
            msg.body(f"Agendamento confirmado para *{nome}* às *{horario}*! ✅")
        return str(resp)

    # Respostas normais
    if 'oi' in incoming_msg:
        msg.body("Olá! 👋 Bem-vindo! Digite:\n1️⃣ Horário\n2️⃣ Cardápio\n3️⃣ Agendar")
    elif incoming_msg == '1':
        msg.body(f"Nosso horário de atendimento é: {mensagens_dict.get('horario')}")
    elif incoming_msg == '2':
        msg.body(f"Aqui está o cardápio: 🍕🍔🥤\n{mensagens_dict.get('cardapio')}")
    elif incoming_msg == '3':
        agendamento_temp[from_number] = {"etapa": 1}
        msg.body("Vamos agendar! Qual o seu nome?")
    else:
        msg.body("Desculpe, não entendi. Digite 'oi' para ver as opções.")
    
    return str(resp)

# ---------------------- ROTAS WEB ----------------------

@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]
        if email == ADMIN_EMAIL and senha == ADMIN_SENHA:
            session["logado"] = True
            return redirect("/painel")
    return render_template("login.html")

@app.route("/painel")
def painel():
    if not session.get("logado"):
        return redirect("/login")
    conn = sqlite3.connect("agendamentos.db")
    c = conn.cursor()
    c.execute("SELECT nome, horario FROM agendamentos ORDER BY id DESC")
    agendamentos = c.fetchall()
    conn.close()
    return render_template("painel.html", agendamentos=agendamentos)

@app.route("/editar", methods=["GET", "POST"])
def editar():
    if not session.get("logado"):
        return redirect("/login")
    conn = sqlite3.connect("agendamentos.db")
    c = conn.cursor()
    if request.method == "POST":
        horario = request.form["horario"]
        cardapio = request.form["cardapio"]
        c.execute("UPDATE mensagens SET valor = ? WHERE chave = 'horario'", (horario,))
        c.execute("UPDATE mensagens SET valor = ? WHERE chave = 'cardapio'", (cardapio,))
        conn.commit()
    c.execute("SELECT chave, valor FROM mensagens")
    mensagens = dict(c.fetchall())
    conn.close()
    return render_template("editar.html", mensagens=mensagens)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
