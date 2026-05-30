from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import unicodedata  # <--- NOVA IMPORTAÇÃO PARA TRATAR ACENTOS
import csv
import re
import os

# CORREÇÃO 1: Mantido sem static_folder padrão para não crashar o ambiente serverless
app = Flask(__name__, static_folder=None)

# ─────────────────────────────────────────────
# Estado da sessão (em memória por simplicidade)
# ─────────────────────────────────────────────
historico_atendimento: list[str] = []
estado_conversa: dict = {"fluxo": None, "etapa": 0, "dados": {}}


# ─────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────

def hora_atual() -> str:
    """Retorna o horário atual formatado HH:MM."""
    return datetime.now().strftime("%H:%M")


def registrar_historico(evento: str) -> None:
    """Registra um evento no histórico de atendimento."""
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    historico_atendimento.append(f"[{ts}] {evento}")


def normalizar(texto: str) -> str:
    """
    Remove de forma robusta todos os acentos, símbolos e cedilhas,
    transformando o texto em minúsculas para um casamento perfeito.
    """
    if not texto:
        return ""
    
    # Converte para minúsculas e remove espaços inúteis nas pontas
    texto = texto.lower().strip()
    
    # Decompõe os caracteres acentuados (Ex: "ã" vira "a" + "~")
    texto_decomposto = unicodedata.normalize('NFD', texto)
    
    # Filtra mantendo apenas as letras base, descartando as marcações de acento
    texto_sem_acento = "".join(ch for ch in texto_decomposto if unicodedata.category(ch) != 'Mn')
    
    # O caractere 'ç' costuma manter a base separada, então garantimos a troca manual por segurança
    return texto_sem_acento.replace('ç', 'c')


# ─────────────────────────────────────────────
# Carregamento de intenções do CSV
# ─────────────────────────────────────────────

def carregar_intencoes(caminho: str = None) -> list[dict]:
    """
    Lê o CSV de intenções e retorna uma lista de dicts.
    Inclui um sistema de fallback caso o arquivo não seja mapeado imediatamente.
    """
    if caminho is None:
        diretorio_bot = os.path.dirname(os.path.abspath(__file__))
        caminho_absoluto = os.path.join(diretorio_bot, "dados.csv")
        
        if os.path.exists(caminho_absoluto):
            caminho = caminho_absoluto
        elif os.path.exists("api/dados.csv"):
            caminho = "api/dados.csv"
        else:
            caminho = "dados.csv"

    dados = []
    try:
        with open(caminho, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                dados.append({
                    "intencao": row["intencao"].strip(),
                    "palavras": [normalizar(p.strip()) for p in row["palavras"].split(",")],
                    "resposta": row["resposta"].strip(),
                })
        return dados
    except Exception as e:
        print(f"Aviso: Não foi possível ler o CSV ({e}). Usando dados de emergência.")
        return [
            {"intencao": "saudacoes", "palavras": ["oi", "ola", "bom dia"], "resposta": "Olá! O bot inicializou com sucesso no Vercel."},
            {"intencao": "nao_entendido", "palavras": [], "resposta": "Não entendi, mas o sistema está online."}
        ]


# Carrega intenções com segurança ao iniciar o servidor
INTENCOES: list[dict] = carregar_intencoes()


def identificar_intencao(msg: str) -> dict | None:
    """Percorre as intenções e retorna a primeira que faz match."""
    for intent in INTENCOES:
        if any(p in msg for p in intent["palavras"]):
            return intent
    return None


# ─────────────────────────────────────────────
# Configuração por intenção
# ─────────────────────────────────────────────
INTENCAO_CONFIG: dict[str, tuple] = {
    "ajuda": (None, "info", ["Formas de pagamento", "Estorno / Reembolso", "Nota Fiscal", "Calcular Frete", "Segunda Via Boleto", "Negociar Divida", "Status Pagamento", "Consultar Imposto", "Desconto"], "Menu de ajuda exibido"),
    "nao_entendido": (None, "erro", ["Formas de pagamento", "Estorno / Reembolso", "Segunda Via Boleto", "Nova conversa"], "Mensagem nao compreendida"),
    "limite_credito": ("limite_credito", "info", [], "Fluxo iniciado: Consulta de Limite de Credito"),
    "saudacoes": (None, "info", ["Formas de pagamento", "Estorno / Reembolso", "Nota Fiscal", "Calcular Frete", "Segunda Via Boleto", "Negociar Divida", "Status Pagamento", "Consultar Imposto"], "Novo atendimento iniciado"),
    "pagamento": (None, "info", ["Segunda Via Boleto", "Status Pagamento", "Nova conversa"], "Consulta: Formas de Pagamento"),
    "desconto": ("desconto", "info", [], "Fluxo iniciado: Desconto"),
    "devolucao": (None, "info", ["Encontrar unidade", "Status Pagamento", "Nova conversa"], "Consulta: Estorno / Reembolso"),
    "d_devolucao": (None, "info", ["Status Pagamento", "Nova conversa"], "Consulta: Detalhes do Reembolso"),
    "nota_fiscal": ("nota_fiscal", "info", [], "Fluxo iniciado: Nota Fiscal"),
    "debito": ("negociar_divida", "alerta", ["Sim, confirmo", "Nao, enganei-me"], "Fluxo iniciado: Negociar Divida"),
    "imposto": ("imposto", "info", [], "Fluxo iniciado: Consultar Imposto"),
    "boleto": ("segunda_via", "info", ["PF - Pessoa Fisica", "PJ - Pessoa Juridica"], "Fluxo iniciado: Segunda Via Boleto"),
    "status": (None, "info", [], "Consulta: Status de Pagamento"),
    "frete": ("frete", "info", [], "Fluxo iniciado: Calcular Frete"),
    "consulta": (None, "info", ["Nova conversa"], "Consulta: Orcamento / Producao"),
    "unidades": (None, "info", ["Nova conversa"], "Consulta: Localizar Unidade"),
    "cancelamento": (None, "info", ["Status Pagamento", "Nova conversa"], "Consulta: Cancelamento"),
    "comprovante": (None, "info", ["Status Pagamento", "Nova conversa"], "Consulta: Comprovante de Pagamento"),
    "falar_atendente": (None, "alerta", ["Nova conversa"], "Transferencia para atendente humano"),
    "alterar_dados": (None, "info", ["Nova conversa"], "Consulta: Alterar Dados Cadastrais"),
    "estorno_atrasado": (None, "alerta", ["Status Pagamento", "Nova conversa"], "Consulta: Estorno Atrasado"),
    "horario_atendimento": (None, "info", ["Nova conversa"], "Consulta: Horario de Atendimento"),
    "despedida": (None, "info", [], "Atendimento finalizado pelo cliente"),
    "erro_pagamento": (None, "erro", ["Status Pagamento", "Nova conversa"], "Consulta: Erro de Pagamento"),
}

FLUXO_ETAPA_INICIAL: dict[str, int] = {
    "nota_fiscal": 1,
    "negociar_divida": 1,
    "imposto": 1,
    "segunda_via": 1,
    "frete": 1,
    "desconto": 1,
    "limite_credito": 1,
}


# ─────────────────────────────────────────────
# Motor de respostas do chatbot
# ─────────────────────────────────────────────

def processar_mensagem(mensagem: str) -> dict:
    global estado_conversa

    msg = normalizar(mensagem)
    now = hora_atual()

    fluxo = estado_conversa.get("fluxo")
    etapa = estado_conversa.get("etapa", 0)

    if fluxo == "nota_fiscal":
        if etapa == 1:
            estado_conversa["dados"]["nome"] = mensagem
            estado_conversa["etapa"] = 2
            registrar_historico(f"Nota Fiscal - nome informado: {mensagem}")
            return {"resposta": "Obrigado! Agora informe o seu CPF:", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 2:
            estado_conversa["dados"]["cpf"] = mensagem
            estado_conversa["etapa"] = 3
            return {"resposta": "Perfeito! Por ultimo, informe o ID do Pedido:", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 3:
            estado_conversa["dados"]["pedido"] = mensagem
            nome = estado_conversa["dados"].get("nome", "")
            registrar_historico(f"Nota Fiscal - solicitacao concluida para {nome}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": "Dados received com sucesso! Sua nota fiscal sera emitida e enviada para o e-mail cadastrado em ate 24 hours uteis. Posso ajudar com mais alguma coisa?",
                "tipo": "sucesso", "opcoes": ["Formas de pagamento", "Status Pagamento", "Nova conversa"], "timestamp": now
            }

    if fluxo == "frete":
        if etapa == 1:
            estado_conversa["dados"]["endereco"] = mensagem
            estado_conversa["etapa"] = 2
            return {"resposta": "Otimo! Agora informe o seu CEP (somente numeros):", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 2:
            cep = re.sub(r"\D", "", mensagem)
            registrar_historico(f"Frete calculated - CEP: {cep}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": f"Frete calculated para o CEP {cep}. PAC: 7-12 dias, R$ 18,90. SEDEX: 2-4 dias, R$ 34,50. Posso ajudar com mais alguma coisa?",
                "tipo": "info", "opcoes": ["Segunda Via Boleto", "Status Pagamento", "Nova conversa"], "timestamp": now
            }

    if fluxo == "segunda_via":
        if etapa == 1:
            tipo_pessoa = "PJ" if any(p in msg for p in ["pj", "juridica", "empresa"]) else "PF"
            estado_conversa["dados"]["tipo"] = tipo_pessoa
            estado_conversa["etapa"] = 2
            registrar_historico(f"Segunda Via Boleto - tipo: {tipo_pessoa}")
            return {"resposta": f"Entendido! Voce e {tipo_pessoa}. Informe o numero do seu CPF/CNPJ:", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 2:
            estado_conversa["dados"]["documento"] = mensagem
            estado_conversa["etapa"] = 3
            return {"resposta": "Agora informe o ID do Pedido ou numero do boleto:", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 3:
            registrar_historico(f"Segunda Via Boleto - concluida, pedido: {mensagem}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": "Segunda via gerada com sucesso! O boleto foi enviado para o e-mail cadastrado. Posso ajudar com mais alguma coisa?",
                "tipo": "sucesso", "opcoes": ["Status Pagamento", "Formas de pagamento", "Nova conversa"], "timestamp": now
            }

    if fluxo == "negociar_divida":
        if etapa == 1:
            if any(p in msg for p in ["sim", "confirmo", "yes", "s"]):
                estado_conversa["etapa"] = 2
                registrar_historico("Negociacao de Divida - confirmada pelo cliente")
                return {"resposta": "Entendido! Vamos negociar. Informe o valor aproximado da sua divida (em R$):", "tipo": "alerta", "opcoes": [], "timestamp": now}
            else:
                estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
                return {"resposta": "Tudo bem! Se precisar de ajuda, e so chamar.", "tipo": "info", "opcoes": ["Formas de pagamento", "Status Pagamento"], "timestamp": now}
        if etapa == 2:
            registrar_historico(f"Negociacao de Divida - valor informado: {mensagem}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": "Proposta de negociacao registrada! Nossa equipe financeira entrara em contato em ate 2 dias uteis. Posso ajudar com mais alguma coisa?",
                "tipo": "sucesso", "opcoes": ["Status Pagamento", "Nova conversa"], "timestamp": now
            }

    if fluxo == "imposto":
        if etapa == 1:
            estado_conversa["dados"]["cnpj"] = mensagem
            estado_conversa["etapa"] = 2
            return {"resposta": "Otimo! Agora informe o Nome Completo do responsavel:", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 2:
            estado_conversa["dados"]["nome"] = mensagem
            estado_conversa["etapa"] = 3
            return {"resposta": "Por ultimo, informe o Nome Fantasia da instituicao:", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 3:
            registrar_historico(f"Consulta de Imposto - concluida para {mensagem}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": "Consulta registrada! O relatorio de impostos sera enviado para o e-mail do CNPJ cadastrado em ate 48 horas uteis.",
                "tipo": "sucesso", "opcoes": ["Status Pagamento", "Nova conversa"], "timestamp": now
            }

    if fluxo == "desconto":
        if etapa == 1:
            estado_conversa["dados"]["produto"] = mensagem
            estado_conversa["etapa"] = 2
            registrar_historico(f"Desconto - produto informado: {mensagem}")
            return {"resposta": "Entendido! Qual a quantidade aproximada do pedido?", "tipo": "info", "opcoes": [], "timestamp": now}
        if etapa == 2:
            estado_conversa["dados"]["quantidade"] = mensagem
            estado_conversa["etapa"] = 3
            return {"resposta": "Qual a forma de pagamento preferida?", "tipo": "info", "opcoes": ["PIX / Transferencia", "Cartao de credito", "Boleto"], "timestamp": now}
        if etapa == 3:
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {"resposta": "Solicitacao de desconto registrada! Entraremos em contato em breve.", "tipo": "sucesso", "opcoes": ["Status Pagamento", "Nova conversa"], "timestamp": now}

    if fluxo == "limite_credito":
        if etapa == 1:
            registrar_historico(f"Limite de Credito - CPF: {mensagem}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {"resposta": "CPF recebido! Analisaremos seu limite em até 1 dia útil.", "tipo": "sucesso", "opcoes": ["Status Pagamento", "Nova conversa"], "timestamp": now}

    if any(p in msg for p in ["nova conversa", "reiniciar", "recomecar", "reset"]):
        estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
        return {"resposta": "Conversa reiniciada! Como posso te ajudar?", "tipo": "info", "opcoes": ["Formas de pagamento", "Estorno / Reembolso", "Nota Fiscal", "Calcular Frete"], "timestamp": now}

    intencao = identificar_intencao(msg)
    if intencao:
        nome = intencao["intencao"]
        cfg = INTENCAO_CONFIG.get(nome)
        if not cfg:
            return {"resposta": intencao["resposta"], "tipo": "info", "opcoes": ["Nova conversa"], "timestamp": now}

        fluxo_novo, tipo, opcoes, log = cfg
        registrar_historico(log)
        if fluxo_novo:
            estado_conversa = {"fluxo": fluxo_novo, "etapa": FLUXO_ETAPA_INICIAL.get(fluxo_novo, 1), "dados": {}}
        return {"resposta": intencao["resposta"], "tipo": tipo, "opcoes": opcoes, "timestamp": now}

    fallback = next((i for i in INTENCOES if i["intencao"] == "nao_entendido"), None)
    resposta_fallback = fallback["resposta"] if fallback else "Desculpe, nao entendi sua mensagem."
    return {"resposta": resposta_fallback, "tipo": "erro", "opcoes": ["Formas de pagamento", "Estorno / Reembolso"], "timestamp": now}


# ─────────────────────────────────────────────
# Rotas da API
# ─────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    dados = request.get_json(force=True, silent=True) or {}
    mensagem = dados.get("mensagem", "").strip()
    if not mensagem:
        return jsonify({"resposta": "Por favor, envie uma mensagem.", "tipo": "erro", "opcoes": [], "timestamp": hora_atual()}), 400
    resultado = processar_mensagem(mensagem)
    return jsonify(resultado)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global estado_conversa
    estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
    return jsonify({"status": "ok", "timestamp": hora_atual()})


@app.route("/api/historico", methods=["GET"])
def api_historico():
    return jsonify({"historico": historico_atendimento, "total": len(historico_atendimento), "timestamp": hora_atual()})


# ─────────────────────────────────────────────
# Rota para servir os arquivos HTML/CSS da pasta 'api/templates'
# ─────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    diretorio_templates = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    
    if path != "" and os.path.exists(os.path.join(diretorio_templates, path)):
        return send_from_directory(diretorio_templates, path)
    
    return send_from_directory(diretorio_templates, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)