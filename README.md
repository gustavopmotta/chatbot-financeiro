# FashionFlow · Chatbot Financeiro

Chatbot de atendimento ao setor financeiro da FashionFlow, desenvolvido com Python (Flask) e interface web responsiva.

## Funcionalidades

- **Formas de pagamento** — consulta as modalidades disponíveis (Pix, cartão, boleto)
- **Estorno / Reembolso** — fluxo guiado para solicitação de devolução de valores
- **Nota Fiscal** — reemissão de nota fiscal por CPF e ID de pedido
- **Calcular Frete** — simulação de frete por CEP de destino
- **Segunda Via de Boleto** — emissão para Pessoa Física (CPF) ou Jurídica (CNPJ)
- **Negociar Dívida** — consulta e opções de parcelamento de débitos em aberto
- **Status de Pagamento** — situação atual do pagamento na sessão
- **Consultar Imposto** — envio de dados fiscais para análise
- **Histórico de Atendimento** — log de todos os eventos da sessão atual

## Requisitos

- Python 3.10 ou superior
- pip

## Como executar

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd chatbot-financeiro
```

### 2. (Opcional) Crie um ambiente virtual

```bash
# Windows
py -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
# Windows (py launcher)
py -m pip install -r requirements.txt

# Linux / macOS
pip install -r requirements.txt
```

### 4. Execute a aplicação

```bash
# Windows
py bot.py

# Linux / macOS
python bot.py
```

### 5. Acesse no navegador

Abra [http://localhost:5000](http://localhost:5000)

## Estrutura do projeto

```
chatbot-financeiro/
├── bot.py              # Servidor Flask + lógica do chatbot
├── requirements.txt    # Dependências Python
├── templates/
│   └── index.html      # Interface web do chat
└── README.md
```

## Tecnologias utilizadas

- **Python 3** + **Flask** — backend e rotas da API
- **HTML5 / CSS3 / JavaScript** — interface web sem dependências externas
- **Google Fonts** (DM Sans + DM Serif Display) — tipografia

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/chat` | Envia mensagem e recebe resposta do bot |
| `GET`  | `/api/historico` | Retorna histórico de eventos da sessão |
| `POST` | `/api/reset` | Reinicia a sessão atual |

### Exemplo de requisição

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Olá"}'
```

### Exemplo de resposta

```json
{
  "resposta": "👗 Olá! Tudo bem?\n\nSomos a **FashionFlow**!...",
  "tipo": "info",
  "opcoes": ["Formas de pagamento", "Estorno / Reembolso", "..."],
  "timestamp": "10:30"
}
```
