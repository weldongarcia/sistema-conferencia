from fastapi import FastAPI

from app.database.connection import engine
from app.models.conferencia import Conferencia

app = FastAPI()

Conferencia.metadata.create_all(bind=engine)
@app.get("/")
def home():
    return {"ok": True}

from app.routes import conferencias
from app.routes import notas
from app.routes import volumes
from app.routes import itens
from app.routes import irregularidades

app = FastAPI(title="Sistema de Conferência")

app.include_router(conferencias.router)
app.include_router(notas.router)
app.include_router(volumes.router)
app.include_router(itens.router)
app.include_router(irregularidades.router)