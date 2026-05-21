import csv

def buscar_respostas():
    perguntas = {}
    respostas = {}

    with open('dados.csv', mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            categoria = row['intencao'].lower()
            palavras = [palavra.strip().lower() for palavra in row['palavras'].split(',')]
            resposta = row['resposta']

            perguntas[categoria] = palavras
            respostas[categoria] = resposta

    return perguntas, respostas

def iniciar_financeiro_fashionflow():
    # Carregando as variáveis do seu CSV para dentro do bot
    perguntas, respostas = buscar_respostas()

    print("FashionFlow: Ola, tudo bem? Somos a FashionFlow!")
    print("Financeiro: Voce esta conversando com o setor Financeiro. Como podemos te ajudar?")
    print("(Digite 'sair' para encerrar)")

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

# Correção dos underlines do dunder main para o código executar
if __name__ == "__main__":
    iniciar_financeiro_fashionflow()