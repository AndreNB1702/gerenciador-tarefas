from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def rota_verificacao():
    return {"status": "rodando", "mensagem": "API inicial"}