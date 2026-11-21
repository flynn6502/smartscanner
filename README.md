# SmartScanner

Web app que lê um PDF com recibos escaneados juntos e entrega um ZIP com **um PDF por recibo**.

## WAMP (recomendado)

Com o Apache do WAMP ligado, abra:

[http://localhost/SmartScanner](http://localhost/SmartScanner)

O PHP recebe o upload e chama o Python (`split_cli.py`) para separar os recibos.

## Flask (opcional)

```bash
python -m pip install -r requirements.txt
python app.py
```

Abra [http://127.0.0.1:5050](http://127.0.0.1:5050).

## Dependências Python

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O endpoint PHP usa o interpretador em `.venv` automaticamente.
