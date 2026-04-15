from fastapi import FastAPI
from app.database.connection import Base, engine
from app.models.contagem import Contagem
from app.routes import contagens
from app.routes import conferencia
from app.models.divergencia import Divergencia

from app.routes import conferencias, notas, volumes, itens, irregularidades

app = FastAPI(title="Sistema de Conferência")

# cria tabelas
print("DIVERGENCIA IMPORTADA")
Base.metadata.create_all(bind=engine)

# rotas
app.include_router(conferencias.router)
app.include_router(notas.router)
app.include_router(volumes.router)
app.include_router(itens.router)
app.include_router(irregularidades.router)
app.include_router(contagens.router)
app.include_router(conferencia.router)

@app.get("/")
def home():
    return {"ok": True}



