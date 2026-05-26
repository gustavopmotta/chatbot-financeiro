from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import re
import os

app = Flask(__name__, static_folder="api", static_url_path="")

# ─────────────────────────────────────────────
# Estado da sessão (em memória por simplicidade)
# ─────────────────────────────────────────────
historico_atendimento: list[str] = []
estado_conversa: dict = {"fluxo": None, "etapa": 0, "dados": {}}


def hora_atual() -> str:
    """Retorna o horário atual formatado HH:MM."""
    return datetime.now().strftime("%H:%M")


def registrar_historico(evento: str) -> None:
    """Registra um evento no histórico de atendimento."""
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    historico_atendimento.append(f"[{ts}] {evento}")


def normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para facilitar matching."""
    mapa = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i", "ó": "o",
        "ô": "o", "õ": "o", "ú": "u", "ü": "u",
        "ç": "c", "ñ": "n",
    }
    texto = texto.lower().strip()
    for orig, rep in mapa.items():
        texto = texto.replace(orig, rep)
    return texto


# ─────────────────────────────────────────────
# Motor de respostas do chatbot
# ─────────────────────────────────────────────
def processar_mensagem(mensagem: str) -> dict:
    """
    Processa a mensagem do usuário e retorna um dicionário com:
      - resposta  : texto da resposta
      - tipo      : categoria da resposta (info, sucesso, erro, alerta)
      - opcoes    : lista de opções rápidas para o usuário
      - timestamp : horário formatado HH:MM
    """
    global estado_conversa

    msg = normalizar(mensagem)
    now = hora_atual()

    # ── Fluxo em andamento ──────────────────────────────────────────────
    fluxo = estado_conversa.get("fluxo")
    etapa = estado_conversa.get("etapa", 0)

    if fluxo == "nota_fiscal":
        if etapa == 1:
            estado_conversa["dados"]["nome"] = mensagem
            estado_conversa["etapa"] = 2
            registrar_historico(f"Nota Fiscal – nome informado: {mensagem}")
            return {
                "resposta": "Obrigado! Agora informe o seu **CPF**:",
                "tipo": "info",
                "opcoes": [],
                "timestamp": now,
            }
        if etapa == 2:
            estado_conversa["dados"]["cpf"] = mensagem
            estado_conversa["etapa"] = 3
            return {
                "resposta": "Perfeito! Por último, informe o **ID do Pedido**:",
                "tipo": "info",
                "opcoes": [],
                "timestamp": now,
            }
        if etapa == 3:
            estado_conversa["dados"]["pedido"] = mensagem
            nome = estado_conversa["dados"].get("nome", "")
            registrar_historico(f"Nota Fiscal – solicitação concluída para {nome}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": (
                    "✅ Dados recebidos com sucesso!\n\n"
                    "Sua **nota fiscal** será emitida e enviada para o e-mail "
                    "cadastrado em até **24 horas úteis**.\n\n"
                    "Posso ajudar com mais alguma coisa?"
                ),
                "tipo": "sucesso",
                "opcoes": ["💳 Formas de pagamento", "🔍 Status Pagamento", "↺ Nova conversa"],
                "timestamp": now,
            }

    if fluxo == "frete":
        if etapa == 1:
            estado_conversa["dados"]["endereco"] = mensagem
            estado_conversa["etapa"] = 2
            return {
                "resposta": "Ótimo! Agora informe o seu **CEP** (somente números):",
                "tipo": "info",
                "opcoes": [],
                "timestamp": now,
            }
        if etapa == 2:
            cep = re.sub(r"\D", "", mensagem)
            registrar_historico(f"Frete calculado – CEP: {cep}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": (
                    f"📦 Frete calculado para o CEP **{cep}**:\n\n"
                    "| Modalidade | Prazo | Valor |\n"
                    "|---|---|---|\n"
                    "| PAC (Correios) | 7–12 dias úteis | R$ 18,90 |\n"
                    "| SEDEX (Correios) | 2–4 dias úteis | R$ 34,50 |\n"
                    "| Transportadora | 5–8 dias úteis | R$ 22,00 |\n\n"
                    "Posso ajudar com mais alguma coisa?"
                ),
                "tipo": "info",
                "opcoes": ["📄 Segunda Via Boleto", "🔍 Status Pagamento", "↺ Nova conversa"],
                "timestamp": now,
            }

    if fluxo == "segunda_via":
        if etapa == 1:
            tipo_pessoa = "PJ" if "pj" in msg or "juridica" in msg or "empresa" in msg else "PF"
            estado_conversa["dados"]["tipo"] = tipo_pessoa
            estado_conversa["etapa"] = 2
            registrar_historico(f"Segunda Via Boleto – tipo: {tipo_pessoa}")
            return {
                "resposta": f"Entendido! Você é **{tipo_pessoa}**. Informe o número do seu **CPF/CNPJ**:",
                "tipo": "info",
                "opcoes": [],
                "timestamp": now,
            }
        if etapa == 2:
            estado_conversa["dados"]["documento"] = mensagem
            estado_conversa["etapa"] = 3
            return {
                "resposta": "Agora informe o **ID do Pedido** ou número do boleto:",
                "tipo": "info",
                "opcoes": [],
                "timestamp": now,
            }
        if etapa == 3:
            registrar_historico(f"Segunda Via Boleto – concluída, pedido: {mensagem}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": (
                    "✅ Segunda via gerada com sucesso!\n\n"
                    "O boleto foi enviado para o **e-mail cadastrado** e também "
                    "estará disponível na sua área do cliente.\n\n"
                    "**Vencimento:** 3 dias úteis a partir de hoje.\n\n"
                    "Posso ajudar com mais alguma coisa?"
                ),
                "tipo": "sucesso",
                "opcoes": ["🔍 Status Pagamento", "💳 Formas de pagamento", "↺ Nova conversa"],
                "timestamp": now,
            }

    if fluxo == "negociar_divida":
        if etapa == 1:
            if "sim" in msg or "s" == msg or "confirmo" in msg or "yes" in msg:
                estado_conversa["etapa"] = 2
                registrar_historico("Negociação de Dívida – confirmada pelo cliente")
                return {
                    "resposta": (
                        "Entendido! Vamos negociar. Informe o **valor aproximado** "
                        "da sua dívida (em R$):"
                    ),
                    "tipo": "alerta",
                    "opcoes": [],
                    "timestamp": now,
                }
            else:
                estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
                return {
                    "resposta": "Tudo bem! Se precisar de ajuda, é só chamar. 😊",
                    "tipo": "info",
                    "opcoes": ["💳 Formas de pagamento", "🔍 Status Pagamento"],
                    "timestamp": now,
                }
        if etapa == 2:
            registrar_historico(f"Negociação de Dívida – valor informado: {mensagem}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": (
                    "✅ Proposta de negociação registrada!\n\n"
                    "Nossa equipe financeira entrará em contato em até **2 dias úteis** "
                    "com as melhores condições de parcelamento.\n\n"
                    "Posso ajudar com mais alguma coisa?"
                ),
                "tipo": "sucesso",
                "opcoes": ["🔍 Status Pagamento", "↺ Nova conversa"],
                "timestamp": now,
            }

    if fluxo == "imposto":
        if etapa == 1:
            estado_conversa["dados"]["cnpj"] = mensagem
            estado_conversa["etapa"] = 2
            return {
                "resposta": "Ótimo! Agora informe o **Nome Completo** do responsável:",
                "tipo": "info",
                "opcoes": [],
                "timestamp": now,
            }
        if etapa == 2:
            estado_conversa["dados"]["nome"] = mensagem
            estado_conversa["etapa"] = 3
            return {
                "resposta": "Por último, informe o **Nome Fantasia** da instituição:",
                "tipo": "info",
                "opcoes": [],
                "timestamp": now,
            }
        if etapa == 3:
            registrar_historico(f"Consulta de Imposto – concluída para {mensagem}")
            estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
            return {
                "resposta": (
                    "✅ Consulta registrada!\n\n"
                    "O relatório de impostos será enviado para o **e-mail do CNPJ** "
                    "cadastrado em até **48 horas úteis**.\n\n"
                    "Posso ajudar com mais alguma coisa?"
                ),
                "tipo": "sucesso",
                "opcoes": ["🔍 Status Pagamento", "↺ Nova conversa"],
                "timestamp": now,
            }

    # ── Intenções de entrada ────────────────────────────────────────────
    if any(p in msg for p in ["ola", "oi", "bom dia", "boa tarde", "boa noite", "hello", "hi"]):
        registrar_historico("Novo atendimento iniciado")
        return {
            "resposta": (
                "Olá! Bem-vindo(a) ao **Assistente Financeiro FashionFlow**! 👋\n\n"
                "Como posso te ajudar hoje? Escolha uma das opções abaixo ou "
                "digite sua dúvida:"
            ),
            "tipo": "info",
            "opcoes": [
                "💳 Formas de pagamento",
                "🔄 Estorno / Reembolso",
                "🧾 Nota Fiscal",
                "🚚 Calcular Frete",
                "📄 Segunda Via Boleto",
                "📋 Negociar Dívida",
                "🔍 Status Pagamento",
                "🏛️ Consultar Imposto",
            ],
            "timestamp": now,
        }

    if any(p in msg for p in ["pagamento", "pagar", "forma", "pix", "cartao", "credito", "debito"]):
        registrar_historico("Consulta: Formas de Pagamento")
        return {
            "resposta": (
                "💳 **Formas de Pagamento aceitas pela FashionFlow:**\n\n"
                "| Método | Detalhes |\n"
                "|---|---|\n"
                "| PIX | Aprovação imediata, disponível 24h |\n"
                "| Cartão de Débito | Aprovação imediata |\n"
                "| Cartão de Crédito | Até 12x sem juros |\n"
                "| Boleto Bancário | Vencimento em 3 dias úteis |\n\n"
                "Posso ajudar com mais alguma coisa?"
            ),
            "tipo": "info",
            "opcoes": ["📄 Segunda Via Boleto", "🔍 Status Pagamento", "↺ Nova conversa"],
            "timestamp": now,
        }

    if any(p in msg for p in ["estorno", "reembolso", "devolver", "devolucao", "devolução"]):
        registrar_historico("Consulta: Estorno / Reembolso")
        return {
            "resposta": (
                "🔄 **Política de Estorno e Reembolso:**\n\n"
                "Iremos reembolsar o seu valor no prazo de **3 dias úteis**.\n\n"
                "Para isso, por favor **devolva a peça de roupa** na nossa unidade "
                "mais próxima de você.\n\n"
                "Deseja localizar a unidade mais próxima?"
            ),
            "tipo": "info",
            "opcoes": ["📍 Encontrar unidade", "🔍 Status Pagamento", "↺ Nova conversa"],
            "timestamp": now,
        }

    if any(p in msg for p in ["nota fiscal", "cupom fiscal", "nf", "nota"]):
        registrar_historico("Fluxo iniciado: Nota Fiscal")
        estado_conversa = {"fluxo": "nota_fiscal", "etapa": 1, "dados": {}}
        return {
            "resposta": (
                "🧾 **Emissão de Nota Fiscal**\n\n"
                "Precisamos de alguns dados do seu pedido. "
                "Por favor, informe o seu **Nome Completo**:"
            ),
            "tipo": "info",
            "opcoes": [],
            "timestamp": now,
        }

    if any(p in msg for p in ["frete", "entrega", "calcular frete", "envio"]):
        registrar_historico("Fluxo iniciado: Calcular Frete")
        estado_conversa = {"fluxo": "frete", "etapa": 1, "dados": {}}
        return {
            "resposta": (
                "🚚 **Calcular Frete**\n\n"
                "Vamos calcular o valor do seu frete! "
                "Informe o seu **endereço completo** (rua, número, cidade, estado):"
            ),
            "tipo": "info",
            "opcoes": [],
            "timestamp": now,
        }

    if any(p in msg for p in ["segunda via", "segunda via boleto", "boleto", "2 via", "2via"]):
        registrar_historico("Fluxo iniciado: Segunda Via Boleto")
        estado_conversa = {"fluxo": "segunda_via", "etapa": 1, "dados": {}}
        return {
            "resposta": (
                "📄 **Segunda Via de Boleto**\n\n"
                "Vamos prosseguir com o andamento da sua segunda via. "
                "Você é **PF (Pessoa Física)** ou **PJ (Pessoa Jurídica)**?"
            ),
            "tipo": "info",
            "opcoes": ["PF – Pessoa Física", "PJ – Pessoa Jurídica"],
            "timestamp": now,
        }

    if any(p in msg for p in ["negociar", "divida", "dívida", "debito", "débito", "inadimplente"]):
        registrar_historico("Fluxo iniciado: Negociar Dívida")
        estado_conversa = {"fluxo": "negociar_divida", "etapa": 1, "dados": {}}
        return {
            "resposta": (
                "📋 **Negociação de Dívida**\n\n"
                "Você está em débito com a nossa empresa? "
                "Confirme para prosseguirmos com o seu atendimento."
            ),
            "tipo": "alerta",
            "opcoes": ["✅ Sim, confirmo", "❌ Não, enganei-me"],
            "timestamp": now,
        }

    if any(p in msg for p in ["status", "status pagamento", "situacao", "situação", "verificar"]):
        registrar_historico("Consulta: Status de Pagamento")
        return {
            "resposta": (
                "🔍 **Status de Pagamento**\n\n"
                "Para verificar o status do seu pagamento, acesse a sua "
                "**área do cliente** em fashionflow.com.br/minha-conta\n\n"
                "Ou informe o **ID do Pedido** que verifico agora mesmo:"
            ),
            "tipo": "info",
            "opcoes": [],
            "timestamp": now,
        }

    if any(p in msg for p in ["imposto", "tributo", "cnpj", "consultar imposto"]):
        registrar_historico("Fluxo iniciado: Consultar Imposto")
        estado_conversa = {"fluxo": "imposto", "etapa": 1, "dados": {}}
        return {
            "resposta": (
                "🏛️ **Consulta de Impostos**\n\n"
                "Para consultar impostos, preciso de alguns dados. "
                "Por favor, informe o seu **CNPJ** (somente números):"
            ),
            "tipo": "info",
            "opcoes": [],
            "timestamp": now,
        }

    if any(p in msg for p in ["unidade", "loja", "endereco", "endereço", "onde", "localizar", "mapa"]):
        registrar_historico("Consulta: Localizar Unidade")
        return {
            "resposta": (
                "📍 **Encontrar Unidade FashionFlow**\n\n"
                "Para encontrar a loja mais perto de você, acesse o nosso "
                "**[Mapa de Lojas](https://fashionflow.com.br/lojas)**\n\n"
                "Ou me envie o seu **CEP** que verifico agora mesmo!"
            ),
            "tipo": "info",
            "opcoes": [],
            "timestamp": now,
        }

    if any(p in msg for p in ["correios", "rastrear", "rastreamento", "tracking"]):
        registrar_historico("Consulta: Rastreamento Correios")
        return {
            "resposta": (
                "📮 **Rastreamento pelos Correios**\n\n"
                "Para rastrear seu pedido, acesse:\n"
                "**[rastreamento.correios.com.br](https://rastreamento.correios.com.br)**\n\n"
                "Informe o **código de rastreio** que está no e-mail de confirmação "
                "de envio. Posso ajudar com mais alguma coisa?"
            ),
            "tipo": "info",
            "opcoes": ["🔍 Status Pagamento", "↺ Nova conversa"],
            "timestamp": now,
        }

    if any(p in msg for p in ["nova conversa", "reiniciar", "recomecar", "recomeçar", "reset"]):
        estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
        registrar_historico("Conversa reiniciada pelo usuário")
        return {
            "resposta": (
                "🔄 Conversa reiniciada!\n\n"
                "Olá novamente! Como posso te ajudar?"
            ),
            "tipo": "info",
            "opcoes": [
                "💳 Formas de pagamento",
                "🔄 Estorno / Reembolso",
                "🧾 Nota Fiscal",
                "🚚 Calcular Frete",
            ],
            "timestamp": now,
        }

    # ── Fallback ────────────────────────────────────────────────────────
    return {
        "resposta": (
            "Desculpe, não entendi sua mensagem. 🤔\n\n"
            "Tente palavras como: **boleto**, **pagamento**, **estorno**, "
            "**frete**, **nota fiscal**, **unidade** ou **correios**."
        ),
        "tipo": "erro",
        "opcoes": [
            "💳 Formas de pagamento",
            "🔄 Estorno / Reembolso",
            "📄 Segunda Via Boleto",
        ],
        "timestamp": now,
    }


# ─────────────────────────────────────────────
# Rotas da API
# ─────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Endpoint principal do chatbot."""
    dados = request.get_json(force=True, silent=True) or {}
    mensagem = dados.get("mensagem", "").strip()
    if not mensagem:
        return jsonify({
            "resposta": "Por favor, envie uma mensagem.",
            "tipo": "erro",
            "opcoes": [],
            "timestamp": hora_atual(),
        }), 400
    resultado = processar_mensagem(mensagem)
    return jsonify(resultado)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reinicia o estado da conversa."""
    global estado_conversa
    estado_conversa = {"fluxo": None, "etapa": 0, "dados": {}}
    registrar_historico("Sessão reiniciada via API")
    return jsonify({"status": "ok", "timestamp": hora_atual()})


@app.route("/api/historico", methods=["GET"])
def api_historico():
    """Retorna o histórico de atendimento."""
    return jsonify({
        "historico": historico_atendimento,
        "total": len(historico_atendimento),
        "timestamp": hora_atual(),
    })


# ─────────────────────────────────────────────
# Servir o frontend estático
# ─────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)