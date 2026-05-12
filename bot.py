def iniciar_financeiro_fashionflow():
    print("FashionFlow: Ola, tudo bem? Somos a FashionFlow!")
    print("Financeiro: Voce esta conversando com o setor Financeiro. Como podemos te ajudar?")
    print("(Digite 'sair' para encerrar)")

    while True:
        
        msg = input("\nVoce: ").lower().strip()

      
        if msg in ['sair', 'encerrar', 'tchau', 'adeus']:
            print("FashionFlow: Atendimento encerrado. Tenha um otimo dia!")
            break

        
        elif "bom dia" in msg or "boa tarde" in msg or "boa noite" in msg or "ola" in msg or "oi" in msg:
            print("FashionFlow: Ola, tudo bem? Somos a FashionFlow! Voce esta conversando com o setor Financeiro. Como podemos te ajudar?")

        
        elif "pagamento" in msg or "cartao" in msg or "a vista" in msg:
            print("FashionFlow: Nossas formas de pagamento sao pix e cartao debito/credito.")

        
        elif "devolver" in msg or "estorno" in msg or "reembolso" in msg:
            print("FashionFlow: Iremos reembolsar o seu valor no prazo de 3 dias, por favor, devolva a peca de roupa na nossa unidade mais proxima de voce!")

        
        elif "nota" in msg or "cupom fiscal" in msg or "nf-e" in msg or "nfe" in msg:
            print("FashionFlow: Precisamos de alguns dados do seu pedido para realizarmos a nova emissao do seu cupom fiscal! Por favor, envie: Nome Completo, CPF e ID do Pedido.")

       
        elif "debito" in msg or "divida" in msg or "dever" in msg or "negociar" in msg or "regularizar" in msg:
            print("FashionFlow: Voce esta em debito com a nossa empresa? Se Sim, confirma pra gente prosseguir com o seu atendimento.")
 
        elif "imposto" in msg or "renda" in msg or "cnpj" in msg:
            print("FashionFlow: Certo! Para consultar impostos, preciso dos dados do: Seu CNPJ; Seu Nome; Nome Fantasia da Instituicao.")

        elif "boleto" in msg or "segunda via" in msg or "nova via" in msg:
            print("FashionFlow: Certo! Vamos prosseguir com o andamento da sua segunda via. Voce e PF ou PJ?")

        elif "status" in msg:
            print("FashionFlow: Ok. Verificamos aqui e o status do seu pagamento e confirmado.")

        elif "frete" in msg or "calcular" in msg:
            print("FashionFlow: Vamos calcular o valor do seu frete. Nos diga o endereco e o CEP.")

        elif "desconto" in msg or "porcentagem" in msg:
            print("FashionFlow: Vamos verificar se e possivel aplicar a taxa de desconto acerca deste lote/produto. Por favor, aguarde que voce sera encaminhado a um dos nossos representantes.")

        elif "consulta" in msg or "orcamento" in msg or "producao" in msg:
            print("FashionFlow: Nos envie a lista de materiais e orcamento estimado, para verificarmos se ha disponibilidade de liberarmos o orcamento.")

        else:
            print("FashionFlow: Desculpe, nao entendi. Tente palavras como: boleto, pagamento, estorno ou nota fiscal.")

if __name__ == "__main__":
    iniciar_financeiro_fashionflow()