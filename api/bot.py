import os
import csv
from flask import Flask, render_template, request, jsonify

# Define a pasta de templates (HTML) de forma dinâmica para o Vercel
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask(__name__, template_folder=template_dir)

def buscar_respostas():
    perguntas = {}
    respostas = {}

    # Caminho dinâmico para encontrar o dados.csv na mesma pasta do bot.py
    caminho_csv = os.path.join(os.path.dirname(__file__), 'dados.csv')

    with open(caminho_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            categoria = row['intencao'].lower()
            palavras = [palavra.strip().lower() for palavra in row['palavras'].split(',')]
            resposta = row['resposta']

            perguntas[categoria] = palavras
            respostas[categoria] = resposta

    return perguntas, respostas

# Rota que carrega a página HTML do seu chat
@app.route('/')
def home():
    return render_template('index.html')

# Rota da API que processa as mensagens enviadas pela interface web
@app.route('/api/chat', methods=['POST'])
def chat_financeiro():
    dados = request.get_json() or {}
    msg = dados.get('mensagem', '').lower().strip()

    if not msg:
        return jsonify({"resposta": "FashionFlow: Por favor, envie uma mensagem válida."}), 400

    palavras_saida = ["ok", "certo", "obrigado", "valeu", "vlw", "ajudou", "pronto", "sair"]

    if msg in palavras_saida:
        return jsonify({"resposta": "Financeiro: Atendimento encerrado. A FashionFlow agradece! Tenha um ótimo dia."})

    # Carrega o dicionário vindo do arquivo CSV
    perguntas, respostas = buscar_respostas()

    # Varre as intenções para encontrar palavras-chave correspondentes
    for categoria, palavras in perguntas.items():
        if any(palavra in msg for palavra in palavras):
            return jsonify({"resposta": f"Financeiro: {respostas[categoria]}"})

    # Resposta padrão caso o bot não encontre palavras-chave conhecidas
    return jsonify({
        "resposta": "FashionFlow: Desculpe, não entendi. Tente palavras como: boleto, pagamento, estorno, unidade ou correios."
    })

if __name__ == "__main__":
    app.run(debug=True)
