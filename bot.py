import re
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = "fashionflow-secret-2026"

#  CAMADA DE DADOS (Tabela de Mapeamento)

class MemoriaAtendimento:
    """Estrutura de dados conforme a Tabela de Mapeamento."""
    def __init__(self):
        self.cpf_cliente:                str   = ""
        self.num_nota_fiscal:            int   = 0
        self.estorno_valor:              float = 0.0
        self.reembolso_valor:            float = 0.0
        self.forma_pagamento:            bool  = True    # True=Digital, False=Dinheiro
        self.status_fatura:              bool  = False   # False=Pendente, True=Pago
        self.confirmacao_estorno:        bool  = False
        self.pagamento_confirmado:       bool  = False
        self.confirmacao_reembolso:      bool  = False
        self.itens_nota:                 list[str] = [] # Matriz de produtos
        self.datas_vencimento_parcelas:  list[str] = []
        self.historico_status_pagamento: list[str] = []
        # Dados auxiliares de fluxo
        self.nome_cliente: str = ""
        self.id_pedido:    str = ""
        self.cnpj:         str = ""
        self.cep:          str = ""
        self.etapa_atual:  str = ""               # controla fluxos multi-turno

    def registrar_historico(self, evento: str):
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.historico_status_pagamento.append(f"[{ts}] {evento}")

    def to_dict(self):
        return self.__dict__

# Sessões em memória (em produção usaria banco de dados)
sessoes: dict[str, MemoriaAtendimento] = {}

def obter_memoria(session_id: str) -> MemoriaAtendimento:
    if session_id not in sessoes:
        sessoes[session_id] = MemoriaAtendimento()
    return sessoes[session_id]

#  MOTOR DE INTENÇÕES (Matriz de Conhecimento)

INTENCOES = [
    {
        "id": "saudacao",
        "keywords": ["bom dia", "boa tarde", "boa noite", "olá", "ola", "oi", "hey", "hello"],
        "prioridade": 1,
    },
    {
        "id": "pagamento",
        "keywords": ["formas de pagamento", "pagamento", "cartão", "cartao", "à vista", "a vista", "pix", "débito", "debito", "crédito", "credito"],
        "prioridade": 2,
    },
    {
        "id": "estorno",
        "keywords": ["devolver", "estorno", "reembolso", "devolução", "devolucao", "restituição", "restituicao"],
        "prioridade": 2,
    },
    {
        "id": "nota_fiscal",
        "keywords": ["nota", "cupom fiscal", "nf-e", "nfe", "nota fiscal", "segunda via nota"],
        "prioridade": 2,
    },
    {
        "id": "negociar_divida",
        "keywords": ["débito", "debito", "dívidas", "dividas", "dever", "negociar", "regularizar", "em débito", "em debito"],
        "prioridade": 2,
    },
    {
        "id": "consultar_imposto",
        "keywords": ["imposto", "renda", "cnpj", "tributo", "fiscal"],
        "prioridade": 2,
    },
    {
        "id": "segunda_via_boleto",
        "keywords": ["boleto", "segunda via", "nova via", "2via", "2ª via"],
        "prioridade": 2,
    },
    {
        "id": "status_pagamento",
        "keywords": ["status", "situação", "situacao", "verificar pagamento", "meu pagamento"],
        "prioridade": 2,
    },
    {
        "id": "calcular_frete",
        "keywords": ["frete", "calcular frete", "entrega", "envio", "cep"],
        "prioridade": 2,
    },
    {
        "id": "desconto",
        "keywords": ["desconto", "porcentagem", "promoção", "promocao", "cupom desconto"],
        "prioridade": 2,
    },
    {
        "id": "orcamento",
        "keywords": ["consulta", "orçamento", "orcamento", "produção", "producao", "disponibilidade"],
        "prioridade": 2,
    },
    {
        "id": "encerrar",
        "keywords": ["obrigado", "tchau", "até mais", "ate mais", "encerrar", "sair", "finalizar", "valeu"],
        "prioridade": 1,
    },
]

def detectar_intencao(texto: str) -> str | None:
    melhor = None
    melhor_score = 0
    texto_lower = texto.lower().strip()

    for intencao in INTENCOES:
        for kw in intencao["keywords"]:
            if kw in texto_lower:
                score = len(kw) * intencao["prioridade"]
                if score > melhor_score:
                    melhor_score = score
                    melhor = intencao["id"]
    return melhor


#  GERADOR DE RESPOSTAS (com fluxos multi-turno)

def gerar_resposta(mensagem: str, memoria: MemoriaAtendimento) -> dict:
    """Retorna dict com 'texto', 'tipo' (info/success/warning/error) e 'opcoes'."""
    texto_lower = mensagem.lower().strip()

    # Fluxos multi-turno em andamento
    etapa = memoria.etapa_atual

    if etapa == "aguardando_confirmacao_estorno":
        if any(w in texto_lower for w in ["sim", "s", "confirmo", "quero", "yes"]):
            memoria.confirmacao_estorno = True
            memoria.confirmacao_reembolso = True
            memoria.etapa_atual = "aguardando_valor_estorno"
            memoria.registrar_historico("Cliente confirmou solicitação de estorno/reembolso")
            return {
                "texto": "✅ Ótimo! Por favor, informe o **valor** que deseja estornar (ex: 150.00):",
                "tipo": "info",
                "opcoes": []
            }
        else:
            memoria.etapa_atual = ""
            return {
                "texto": "Tudo bem! Se precisar de mais alguma coisa, é só chamar. 😊",
                "tipo": "info",
                "opcoes": ["Voltar ao menu", "Encerrar atendimento"]
            }

    if etapa == "aguardando_valor_estorno":
        valor_match = re.search(r"[\d]+[.,]?[\d]*", mensagem.replace(",", "."))
        if valor_match:
            valor = float(valor_match.group().replace(",", "."))
            memoria.estorno_valor = valor
            memoria.reembolso_valor = valor
            memoria.etapa_atual = ""
            memoria.registrar_historico(f"Estorno de R$ {valor:.2f} solicitado")
            return {
                "texto": f"💸 Estorno de **R$ {valor:.2f}** registrado com sucesso!\n\n"
                         f"O reembolso será processado em até **3 dias úteis**.\n"
                         f"Por favor, devolva a peça na nossa unidade mais próxima com o número do pedido.",
                "tipo": "success",
                "opcoes": ["Verificar status do reembolso", "Encerrar atendimento"]
            }
        else:
            return {
                "texto": "⚠️ Não consegui identificar o valor. Por favor, informe apenas o número (ex: 89.90):",
                "tipo": "warning",
                "opcoes": []
            }

    if etapa == "aguardando_dados_nota":
        memoria.registrar_historico(f"Dados para nota fiscal fornecidos: {mensagem[:50]}")
        num = 100000 + len(sessoes)
        memoria.num_nota_fiscal = num
        memoria.etapa_atual = ""
        return {
            "texto": f"📄 Dados recebidos! Sua nota fiscal **Nº {num}** está sendo reemitida.\n\n"
                     f"Você receberá o documento no e-mail cadastrado em até **2 horas úteis**.",
            "tipo": "success",
            "opcoes": ["Preciso de mais ajuda", "Encerrar atendimento"]
        }

    if etapa == "aguardando_confirmacao_divida":
        if any(w in texto_lower for w in ["sim", "s", "confirmo", "yes"]):
            memoria.etapa_atual = "aguardando_dados_divida"
            memoria.registrar_historico("Cliente confirmou débito pendente")
            return {
                "texto": "📋 Entendido! Para consultarmos sua dívida, precisamos:\n\n"
                         "• **CPF** do titular\n"
                         "• **Número do pedido** (se tiver)\n\n"
                         "Por favor, envie essas informações:",
                "tipo": "info",
                "opcoes": []
            }
        else:
            memoria.etapa_atual = ""
            return {
                "texto": "Sem problemas! Se precisar de qualquer outra informação, estou aqui. 😊",
                "tipo": "info",
                "opcoes": ["Ver formas de pagamento", "Encerrar atendimento"]
            }

    if etapa == "aguardando_dados_divida":
        memoria.etapa_atual = ""
        memoria.registrar_historico(f"Dados de débito fornecidos: {mensagem[:50]}")
        return {
            "texto": "🔍 Encontramos um débito em aberto no seu cadastro.\n\n"
                     "**Condições de negociação disponíveis:**\n"
                     "• À vista com **10% de desconto**\n"
                     "• Em até **3x sem juros** no cartão\n"
                     "• **Pix** com quitação imediata\n\n"
                     "Deseja prosseguir com alguma dessas opções?",
            "tipo": "warning",
            "opcoes": ["Pagar à vista (10% off)", "Parcelar em 3x", "Pagar via Pix", "Falar com atendente"]
        }

    if etapa == "aguardando_dados_imposto":
        memoria.etapa_atual = ""
        memoria.registrar_historico(f"Dados fiscais fornecidos: {mensagem[:50]}")
        return {
            "texto": "📊 Dados recebidos! Nossa equipe fiscal irá processar a consulta.\n\n"
                     "O relatório de impostos será enviado para o e-mail vinculado ao CNPJ informado em até **1 dia útil**.",
            "tipo": "success",
            "opcoes": ["Preciso de mais ajuda", "Encerrar atendimento"]
        }

    if etapa == "aguardando_tipo_segunda_via":
        memoria.etapa_atual = "aguardando_dados_segunda_via"
        tipo = "Pessoa Jurídica" if any(w in texto_lower for w in ["pj", "jurídica", "juridica", "empresa", "cnpj"]) else "Pessoa Física"
        memoria.registrar_historico(f"Segunda via solicitada - {tipo}")
        return {
            "texto": f"👤 Identificado como **{tipo}**.\n\n"
                     f"Para emitir a segunda via do boleto, informe:\n"
                     f"• {'CNPJ' if tipo == 'Pessoa Jurídica' else 'CPF'}\n"
                     f"• Número do pedido ou da fatura",
            "tipo": "info",
            "opcoes": []
        }

    if etapa == "aguardando_dados_segunda_via":
        memoria.etapa_atual = ""
        memoria.registrar_historico("Segunda via de boleto emitida")
        return {
            "texto": "✅ Segunda via gerada com sucesso!\n\n"
                     "O boleto foi enviado para o seu **e-mail cadastrado**.\n"
                     "Vencimento: em **3 dias úteis** a partir de hoje.\n\n"
                     "_Caso não encontre o e-mail, verifique a pasta de spam._",
            "tipo": "success",
            "opcoes": ["Preciso de mais ajuda", "Encerrar atendimento"]
        }

    if etapa == "aguardando_cep_frete":
        memoria.cep = mensagem.strip()
        memoria.etapa_atual = ""
        cep_num = re.sub(r"\D", "", mensagem)
        # Simulação de cálculo de frete por faixa de CEP
        if cep_num and len(cep_num) >= 5:
            prefixo = int(cep_num[:2])
            if prefixo <= 20:
                frete, prazo = 12.90, "2-3 dias úteis"
            elif prefixo <= 50:
                frete, prazo = 18.90, "3-5 dias úteis"
            elif prefixo <= 70:
                frete, prazo = 24.90, "5-7 dias úteis"
            else:
                frete, prazo = 34.90, "7-10 dias úteis"
            memoria.registrar_historico(f"Frete calculado para CEP {memoria.cep}: R$ {frete}")
            return {
                "texto": f"🚚 Cálculo de frete para o CEP **{memoria.cep}**:\n\n"
                         f"| Modalidade | Valor | Prazo |\n"
                         f"|---|---|---|\n"
                         f"| Padrão | R$ {frete:.2f} | {prazo} |\n"
                         f"| Expresso | R$ {frete*1.8:.2f} | 1-2 dias úteis |\n"
                         f"| Econômico | R$ {frete*0.7:.2f} | {prazo.split('-')[1].strip()} |\n\n"
                         f"_Frete grátis em compras acima de R$ 299,90_ 🎉",
                "tipo": "success",
                "opcoes": ["Calcular outro CEP", "Preciso de mais ajuda"]
            }
        else:
            return {
                "texto": "⚠️ CEP inválido. Por favor, informe um CEP válido (ex: 01310-100):",
                "tipo": "warning",
                "opcoes": []
            }

    # ── Detecção de intenção nova ─────────────────────────────────────────────
    intencao = detectar_intencao(mensagem)

    if intencao == "saudacao":
        memoria.registrar_historico("Atendimento iniciado")
        return {
            "texto": "👗 Olá! Tudo bem?\n\nSomos a **FashionFlow**! Você está conversando com o setor **Financeiro**.\n\nComo podemos te ajudar hoje?",
            "tipo": "info",
            "opcoes": ["Formas de pagamento", "Estorno / Reembolso", "Nota Fiscal", "Calcular Frete", "Segunda Via de Boleto", "Negociar Dívida"]
        }

    elif intencao == "pagamento":
        memoria.registrar_historico("Consulta sobre formas de pagamento")
        return {
            "texto": "💳 Nossas formas de pagamento são:\n\n"
                     "• **Pix** — Aprovação imediata\n"
                     "• **Cartão de Débito** — Aprovação imediata\n"
                     "• **Cartão de Crédito** — Parcelável em até 12x\n"
                     "• **Boleto Bancário** — Prazo de 3 dias úteis\n\n"
                     "_Pagamentos acima de R$ 500 em cartão de crédito são elegíveis para parcelamento sem juros._",
            "tipo": "info",
            "opcoes": ["Preciso de segunda via de boleto", "Ver políticas de desconto", "Encerrar atendimento"]
        }

    elif intencao == "estorno":
        memoria.etapa_atual = "aguardando_confirmacao_estorno"
        return {
            "texto": "🔄 Entendido! Vamos iniciar o processo de **estorno/reembolso**.\n\n"
                     "Antes de prosseguir, confirme: você deseja solicitar o reembolso de uma compra?",
            "tipo": "info",
            "opcoes": ["Sim, quero o reembolso", "Não, era outra dúvida"]
        }

    elif intencao == "nota_fiscal":
        memoria.etapa_atual = "aguardando_dados_nota"
        return {
            "texto": "🧾 Vamos reemitir sua nota fiscal!\n\n"
                     "Por favor, envie as seguintes informações em uma única mensagem:\n\n"
                     "• **Nome Completo**\n"
                     "• **CPF**\n"
                     "• **ID do Pedido**",
            "tipo": "info",
            "opcoes": []
        }

    elif intencao == "negociar_divida":
        memoria.etapa_atual = "aguardando_confirmacao_divida"
        return {
            "texto": "📋 Vamos verificar sua situação financeira com a FashionFlow.\n\n"
                     "Você possui algum **débito em aberto** com a nossa empresa?",
            "tipo": "warning",
            "opcoes": ["Sim, tenho débito", "Não tenho débito"]
        }

    elif intencao == "consultar_imposto":
        memoria.etapa_atual = "aguardando_dados_imposto"
        return {
            "texto": "🏛️ Para consultar impostos, precisamos dos seguintes dados:\n\n"
                     "• **CNPJ** da instituição\n"
                     "• **Nome Completo** do responsável\n"
                     "• **Nome Fantasia** da Instituição\n\n"
                     "Por favor, envie essas informações:",
            "tipo": "info",
            "opcoes": []
        }

    elif intencao == "segunda_via_boleto":
        memoria.etapa_atual = "aguardando_tipo_segunda_via"
        return {
            "texto": "📄 Vamos emitir a **segunda via do seu boleto**!\n\nVocê é:",
            "tipo": "info",
            "opcoes": ["Pessoa Física (CPF)", "Pessoa Jurídica (CNPJ)"]
        }

    elif intencao == "status_pagamento":
        # Simulação de status
        status = "✅ **PAGO**" if memoria.pagamento_confirmado else "⏳ **PENDENTE**"
        forma = "Digital (Pix/Cartão)" if memoria.forma_pagamento else "Dinheiro"
        memoria.registrar_historico("Consulta de status de pagamento")
        return {
            "texto": f"🔍 Status do seu pagamento:\n\n"
                     f"**Status:** {status}\n"
                     f"**Forma:** {forma}\n\n"
                     f"_Para detalhes específicos de um pedido, informe o número do pedido._",
            "tipo": "info",
            "opcoes": ["Preciso de segunda via", "Ver histórico", "Encerrar atendimento"]
        }

    elif intencao == "calcular_frete":
        memoria.etapa_atual = "aguardando_cep_frete"
        return {
            "texto": "🚚 Vamos calcular o frete para você!\n\nPor favor, informe o **CEP de destino**:",
            "tipo": "info",
            "opcoes": []
        }

    elif intencao == "desconto":
        memoria.registrar_historico("Consulta sobre políticas de desconto")
        return {
            "texto": "🏷️ Vamos verificar a possibilidade de aplicar desconto!\n\n"
                     "Nossa equipe de representantes irá analisar o seu pedido.\n\n"
                     "**Aguarde** — você será encaminhado a um dos nossos representantes em breve.\n\n"
                     "_Tempo médio de espera: 5-10 minutos_",
            "tipo": "warning",
            "opcoes": ["Enquanto isso, ver promoções ativas", "Encerrar atendimento"]
        }

    elif intencao == "orcamento":
        memoria.registrar_historico("Consulta de orçamento iniciada")
        return {
            "texto": "📦 Para consultar disponibilidade de orçamento, precisamos:\n\n"
                     "• **Lista de materiais** necessários\n"
                     "• **Orçamento estimado** (valor em R$)\n"
                     "• **Prazo desejado** para a produção\n\n"
                     "Por favor, envie essas informações para análise:",
            "tipo": "info",
            "opcoes": []
        }

    elif intencao == "encerrar":
        memoria.registrar_historico("Atendimento encerrado pelo cliente")
        return {
            "texto": "👋 Obrigado por entrar em contato com a **FashionFlow**!\n\n"
                     "Ficamos à disposição sempre que precisar. Tenha um ótimo dia! 🌟",
            "tipo": "success",
            "opcoes": ["Iniciar novo atendimento"]
        }

    else:
        return {
            "texto": "🤔 Não entendi completamente sua solicitação.\n\n"
                     "Pode reformular ou escolher uma das opções abaixo?",
            "tipo": "warning",
            "opcoes": ["Formas de pagamento", "Estorno / Reembolso", "Nota Fiscal",
                       "Calcular Frete", "Segunda Via de Boleto", "Falar com atendente"]
        }

#  ROTAS FLASK

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensagem = data.get("mensagem", "").strip()
    session_id = session.get("session_id", str(uuid.uuid4()))

    if not mensagem:
        return jsonify({"erro": "Mensagem vazia"}), 400

    memoria = obter_memoria(session_id)
    resposta = gerar_resposta(mensagem, memoria)

    return jsonify({
        "resposta": resposta["texto"],
        "tipo": resposta.get("tipo", "info"),
        "opcoes": resposta.get("opcoes", []),
        "timestamp": datetime.now().strftime("%H:%M"),
    })


@app.route("/api/historico", methods=["GET"])
def historico():
    session_id = session.get("session_id", "")
    memoria = obter_memoria(session_id)
    return jsonify({"historico": memoria.historico_status_pagamento})


@app.route("/api/reset", methods=["POST"])
def reset():
    session_id = session.get("session_id", str(uuid.uuid4()))
    sessoes[session_id] = MemoriaAtendimento()
    session["session_id"] = session_id
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
