from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import engine, get_db

# =================================================================
# CRITICAL: CREACIÓN DE LA BASE DE DATOS Y TABLAS
# Esta línea busca el archivo 'smat.db' y crea las tablas
# definidas en models.py si es que aún no existen.
# =================================================================
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SMAT - Sistema de Monitoreo de Alerta Temprana",
    description="""
API robusta para la gestión y monitoreo de desastres naturales.
Permite la telemetría de sensores en tiempo real y el cálculo de niveles de riesgo.

**Entidades principales:**
* **Estaciones:** Puntos de monitoreo físico (ríos, volcanes, zonas sísmicas).
* **Lecturas:** Datos capturados por sensores en tiempo real.
* **Riesgos:** Análisis de criticidad basado en umbrales predefinidos.
    """,
    version="1.0.0",
    terms_of_service="http://unmsm.edu.pe/terms/",
    contact={
        "name": "Soporte Técnico SMAT - FISI",
        "url": "http://fisi.unmsm.edu.pe",
        "email": "desarrollo.smat@unmsm.edu.pe",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# Esquemas de validación (Pydantic)
class EstacionCreate(BaseModel):
    id: int
    nombre: str
    ubicacion: str

class LecturaCreate(BaseModel):
    estacion_id: int
    valor: float

# ENDPOINTS REFACTORIZADOS
@app.post(
    "/estaciones/",
    status_code=201,
    tags=["Gestión de Infraestructura"],
    summary="Registrar una nueva estación de monitoreo",
    description="Inserta una estación física en la base de datos relacional para el seguimiento de riesgos."
)
def crear_estacion(estacion: EstacionCreate, db: Session = Depends(get_db)):
    # Convertimos el esquema de Pydantic a Modelo de SQLAlchemy
    nueva_estacion = models.EstacionDB(id=estacion.id, nombre=estacion.nombre, ubicacion=estacion.ubicacion)
    db.add(nueva_estacion)
    db.commit()
    db.refresh(nueva_estacion)
    return {"msj": "Estación guardada en DB", "data": nueva_estacion}

@app.post(
    "/lecturas/",
    status_code=201,
    tags=["Telemetría de Sensores"],
    summary="Recibir datos de telemetría (IoT)",
    description="Recibe el valor capturado por un sensor HTTP y lo vincula a una estación existente."
)
def registrar_lectura(lectura: LecturaCreate, db: Session = Depends(get_db)):
    # Validar si la estación existe en la DB
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == lectura.estacion_id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")
    
    nueva_lectura = models.LecturaDB(valor=lectura.valor, estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return {"status": "Lectura guardada en DB"}

@app.get(
    "/estaciones/{id}/historial",
    tags=["Reportes Históricos"],
    summary="Obtener resumen estadístico de lecturas",
    description="Calcula el conteo total y el promedio de las lecturas de una estación."
)
def obtener_historial(id: int, db: Session = Depends(get_db)):
    # 1. Validar si la estación existe en la DB
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no encontrada")
    
    # 2. Consultar todas las lecturas de esa estación en la DB
    lecturas_db = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    
    # 3. Extraer solo los valores para el cálculo
    valores = [l.valor for l in lecturas_db]
    
    # 4. Calcular promedio (evitando división por cero)
    promedio = sum(valores) / len(valores) if valores else 0.0
    
    return {
        "estacion_id": id,
        "lecturas": valores,
        "conteo": len(valores),
        "promedio": round(promedio, 2)
    }