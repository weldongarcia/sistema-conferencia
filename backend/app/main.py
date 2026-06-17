from fastapi import FastAPI
from app.database.connection import Base, engine
from app.models.contagem import Contagem
from app.routes import contagens
from app.routes import conferencia
from app.models.divergencia import Divergencia
from app.models.contagem_historico import ContagemHistorico
from app.routes import conferencias, notas, volumes, itens, irregularidades
from fastapi.security import HTTPBearer
from app.routes import auth
from app.routes import itens
from app.routes import divergencias
from app.models.conferencia_historico import ConferenciaHistorico





app = FastAPI(title="Sistema de Conferência")
security = HTTPBearer()

# cria tabelas

Base.metadata.create_all(bind=engine)

# rotas
app.include_router(conferencias.router)
app.include_router(notas.router)
app.include_router(volumes.router)
app.include_router(itens.router)
app.include_router(irregularidades.router)
app.include_router(contagens.router)
app.include_router(conferencia.router)
app.include_router(auth.router)
app.include_router(divergencias.router)




@app.get("/")
def home():
    return {"ok": True}



