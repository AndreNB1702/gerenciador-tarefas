from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TarefaBD(Base):
    __tablename__ = "tarefas"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

class TarefaSchema(BaseModel):
    titulo: str

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

@app.get("/")
def rota_verificacao():
    return {"status": "rodando", "banco_configurado": True}

@app.get("/tarefas")
def listar_tarefas(db: Session = Depends(get_db)):
    return db.query(TarefaBD).all()

@app.post("/tarefas")
def criar_tarefa(tarefa: TarefaSchema, db: Session = Depends(get_db)):
    nova_tarefa = TarefaBD(titulo=tarefa.titulo)
    db.add(nova_tarefa)
    db.commit()
    db.refresh(nova_tarefa)
    return nova_tarefa

@app.delete("/tarefas/{tarefa_id}")
def deletar_tarefa(tarefa_id: int, db: Session = Depends(get_db)):
    tarefa = db.query(TarefaBD).filter(TarefaBD.id == tarefa_id).first()
    
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    db.delete(tarefa)
    db.commit()
    return {"status": "sucesso", "mensagem": "Tarefa removida"}