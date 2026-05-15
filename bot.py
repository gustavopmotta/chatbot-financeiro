perguntas = {
    "saudacoes": ["bom dia", "boa tarde", "boa noite", "ola", "oi", "hey", "alguem"],
    "pagamento": ["pagamento", "cartao", "a vista", "paguei", "pgto", "deb", "cred", "forma de pagar"],
    "devolucao": ["devolver", "estorno", "reembolso", "devolucao", "destroca", "devolve", "queria meu dinheiro"],
    "d_devolucao": ["conta", "pix", "cartão", "crédito", "dinheiro", "transferência", "banco", "pagar", "qd", "recebo", "cai", "como recebo"],
    "unidades": ["loja", "unidade", "onde", "endereco", "proxima", "perto", "localizacao", "local"],
    "nota_fiscal": ["nota", "cupom fiscal", "nf-e", "nfe", "nf", "comprovante", "danfe", "papel"],
    "debito": ["debito", "divida", "dever", "negociar", "regularizar", "pendencia", "atrasado", "nome sujo"],
    "imposto": ["imposto", "renda", "cnpj", "taxa", "tributo", "leão"],
    "boleto": ["boleto", "segunda via", "nova via", "bol", "2 via", "atualizar boleto", "linha digitavel"],
    "status": ["status", "situacao", "andamento", "verificar", "onde esta", "confirmado"],
    "frete": ["frete", "calcular", "entrega", "valor envio", "cep", "transportadora", "correios", "postar", "enviar", "envio", "etiqueta", "codigo", "logistica", "postagem", "longe", "moro fora"],
    "desconto": ["desconto", "porcentagem", "abatimento", "cupom", "off", "%", "mais barato"],
    "consulta": ["consulta", "orcamento", "producao", "orc", "valor", "tabela", "preço"]
}

respostas = {
    "saudacoes": "Ola, tudo bem? Somos a FashionFlow! Voce esta conversando com o setor Financeiro. Como podemos te ajudar?",
    "pagamento": "Nossas formas de pagamento sao pix e cartao debito/credito (parcelamos em ate 6x sem juros).",
    "devolucao": "Iremos reembolsar o seu valor no prazo de 3 dias úteis após o recebimento, por favor, devolva a peca de roupa na nossa unidade mais proxima de voce!",
    "d_devolucao": "O reembolso é feito pelo mesmo método que você utilizou no pagamento:\n- PIX: Cai direto na conta de origem.\n- Cartão: O estorno aparecerá na sua fatura (em até 2 faturas).\n- Boleto: Entraremos em contato para pedir seus dados bancários.",
    "unidades": "Para encontrar a loja mais perto de você, basta clicar neste link: [Link do Mapa de Lojas] ou me enviar o seu CEP que eu verifico agora mesmo!",
    "nota_fiscal": "Precisamos de alguns dados do seu pedido para realizarmos a nova emissao do seu cupom fiscal! Por favor, envie: Nome Completo, CPF e ID do Pedido.",
    "debito": "Voce esta em debito com a nossa empresa? Se Sim, confirma pra gente prosseguir com o seu atendimento e localizarmos sua pendencia.",
    "imposto": "Certo! Para consultar impostos ou retenções, informe: Seu CNPJ; Seu Nome; Nome Fantasia da Instituicao.",
    "boleto": "Certo! Vamos prosseguir com o andamento da sua segunda via. Voce e PF ou PJ?",
    "status": "Ok. Verificamos aqui e o status do seu pagamento e confirmado e o pedido ja seguiu para separacao.",
    "frete": "Para calcular o frete ou realizar postagem (Correios/Logística), informe o seu CEP. Se você mora fora ou longe de uma unidade, podemos gerar um código de postagem reversa!",
    "desconto": "Vamos verificar se e possivel aplicar a taxa de desconto acerca deste lote/produto. Por favor, aguarde que voce sera encaminhado a um dos nossos representantes.",
    "consulta": "Para orçamentos de produção, nos envie a lista de materiais e volume estimado para verificarmos a disponibilidade."
}

def iniciar_financeiro_fashionflow():
    print("FashionFlow: Ola, tudo bem? Somos a FashionFlow!")
    print("Financeiro: Voce esta conversando com o setor Financeiro. Como podemos te ajudar?")
    print("(Digite 'sair' ou 'obrigado' para encerrar)")

    while True:
        msg = input("\nVoce: ").lower().strip()

        palavras_saida = ["ok", "certo", "obrigado", "valeu", "vlw", "ajudou", "pronto", "sair"]
        
        if msg in palavras_saida:
            print("Financeiro: Atendimento encerrado. A FashionFlow agradece! Tenha um otimo dia.")
            break

        encontrou = False
        for categoria, palavras in perguntas.items():
            if any(palavra in msg for palavra in palavras):
                print(f"Financeiro: {respostas[categoria]}")
                encontrou = True
                break
        
        if not encontrou:
            print("FashionFlow: Desculpe, nao entendi. Tente palavras como: boleto, pagamento, estorno, unidade ou correios.")

if __name__ == "__main__":
    iniciar_financeiro_fashionflow()