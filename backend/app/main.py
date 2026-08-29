from fastapi import FastAPI
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import Base, engine

from app.models.contagem import Contagem
from app.models.divergencia import Divergencia
from app.models.contagem_historico import ContagemHistorico
from app.models.conferencia_historico import ConferenciaHistorico
from app.routes import usuario


from app.routes import (
    contagens,
    conferencia,
    conferencias,
    notas,
    volumes,
    itens,
    irregularidades,
    auth,
    divergencias,
)

app = FastAPI(title="Sistema de Conferência")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ==========================================================
# CRIA TABELAS
# ==========================================================

Base.metadata.create_all(bind=engine)

# ==========================================================
# ROTAS
# ==========================================================

app.include_router(conferencias.router)
app.include_router(notas.router)
app.include_router(volumes.router)
app.include_router(itens.router)
app.include_router(irregularidades.router)
app.include_router(contagens.router)
app.include_router(conferencia.router)
app.include_router(auth.router)
app.include_router(divergencias.router)
app.include_router(usuario.router)

@app.get("/")
def home():
    return {"ok": True}