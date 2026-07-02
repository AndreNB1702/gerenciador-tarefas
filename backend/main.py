from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os
import time

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS DE DADOS ---
class ProdutoBD(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False, default=0)
    preco = Column(Float, nullable=False, default=0.0)

class UsuarioBD(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False) # 'admin' ou 'usuario'

# --- ESPERA O BANCO FICAR PRONTO (evita crash no docker compose up) ---
def aguardar_banco(tentativas=15, intervalo=2):
    for i in range(1, tentativas + 1):
        try:
            conexao = engine.connect()
            conexao.close()
            print("Banco de dados conectado com sucesso.")
            return
        except OperationalError:
            print(f"Banco ainda não está pronto (tentativa {i}/{tentativas}). Aguardando {intervalo}s...")
            time.sleep(intervalo)
    raise RuntimeError("Não foi possível conectar ao banco de dados após várias tentativas.")

aguardar_banco()

Base.metadata.create_all(bind=engine)

# --- SEED DE USUÁRIOS PADRÃO ---
def seed_usuarios():
    db = SessionLocal()
    try:
        usuarios_padrao = [
            {"username": "usuario", "password": "123", "role": "usuario"},
            {"username": "admin", "password": "123", "role": "admin"},
        ]
        for dados in usuarios_padrao:
            existente = db.query(UsuarioBD).filter(UsuarioBD.username == dados["username"]).first()
            if not existente:
                db.add(UsuarioBD(**dados))
        db.commit()
    finally:
        db.close()

seed_usuarios()

# --- SCHEMAS E APP ---
class ProdutoSchema(BaseModel):
    nome: str
    quantidade: int = Field(..., ge=0)
    preco: float = Field(..., ge=0.0)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROTAS DE AUTENTICAÇÃO ---
@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(UsuarioBD).filter(UsuarioBD.username == username, UsuarioBD.password == password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"role": user.role}

# --- ROTAS DE PRODUTO ---
@app.get("/")
def rota_verificacao():
    return {"status": "rodando", "sistema": "estoque-com-login"}

@app.get("/produtos")
def listar_produtos(db: Session = Depends(get_db)):
    return db.query(ProdutoBD).all()

@app.post("/produtos")
def criar_produto(produto: ProdutoSchema, db: Session = Depends(get_db)):
    novo_produto = ProdutoBD(nome=produto.nome, quantidade=produto.quantidade, preco=produto.preco)
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    return novo_produto

@app.delete("/produtos/{produto_id}")
def deletar_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(ProdutoBD).filter(ProdutoBD.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    db.delete(produto)
    db.commit()
    return {"status": "sucesso"}

@app.put("/produtos/{produto_id}/comprar")
def comprar_produto(produto_id: int, quantidade_comprada: int, db: Session = Depends(get_db)):
    produto = db.query(ProdutoBD).filter(ProdutoBD.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if produto.quantidade < quantidade_comprada:
        raise HTTPException(status_code=400, detail="Quantidade insuficiente")
    produto.quantidade -= quantidade_comprada
    db.commit()
    return {"status": "sucesso", "estoque_atual": produto.quantidade}