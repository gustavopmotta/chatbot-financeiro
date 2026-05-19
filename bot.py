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
    print("FashionFlow: Ola, tudo bem? Somos a FashionFlow!")
    print("Financeiro: Voce esta conversando com o setor Financeiro. Como podemos te ajudar?")
    print("(Digite 'sair' para encerrar)")

    while True:
        
        msg = input("\nVoce: ").lower().strip()

        perguntas, respostas = buscar_respostas()

        for categoria, palavras in perguntas.items():
            if any(palavra in msg for palavra in palavras):
                print(f"Financeiro: {respostas[categoria]}")
                break
        else:
            print("FashionFlow: Desculpe, nao entendi. Tente palavras como: boleto, pagamento, estorno ou nota fiscal.")

if __name__ == "__main__":
    iniciar_financeiro_fashionflow()