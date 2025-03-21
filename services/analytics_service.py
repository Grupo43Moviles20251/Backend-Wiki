import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, HTTPException
from datetime import datetime

from pydantic import BaseModel

class ScreenTimeData(BaseModel):
    screen_name: str
    duration: int
    timestamp: str


# Inicializa la aplicación de Firebase con el archivo de credenciales
cred = credentials.Certificate("../app/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

app = FastAPI()

# Ejemplo de conexión a Firestore (Crashlytics no está directamente soportado en Python)
db = firestore.client()

@app.get("/features-usage")
def get_features_usage():
    try:
        features_ref = db.collection("feature_usage").stream()
        usage_by_month = {}

        for feature in features_ref:
            data = feature.to_dict()
            doc_id = feature.id  # El nombre del documento es la fecha (YYYY-MM-DD)
            
            # Extraer el mes del ID del documento
            try:
                month = datetime.strptime(doc_id, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue  # Ignorar si el ID no tiene el formato esperado

            # Inicializar el mes en el diccionario si no existe
            if month not in usage_by_month:
                usage_by_month[month] = {}

            # Sumar los accesos por cada funcionalidad
            for feature_name, count in data.items():
                if feature_name == "last_used_by":
                    continue  # Ignorar el campo de usuario
                if feature_name not in usage_by_month[month]:
                    usage_by_month[month][feature_name] = 0
                usage_by_month[month][feature_name] += count

        return {"features_usage_by_month": usage_by_month}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el uso de funcionalidades: {str(e)}")


@app.get("/features-increasing-rate")
def get_features_increasing_rate():
    try:
        features_ref = db.collection("feature_usage").stream()
        usage_by_month = {}

        # Paso 1: Agrupar los datos por mes
        for feature in features_ref:
            data = feature.to_dict()
            doc_id = feature.id  # El nombre del documento es la fecha (YYYY-MM-DD)

            # Extraer el mes del ID del documento
            try:
                month = datetime.strptime(doc_id, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue  # Ignorar si el ID no tiene el formato esperado

            # Inicializar el mes en el diccionario si no existe
            if month not in usage_by_month:
                usage_by_month[month] = {}

            # Sumar los accesos por cada funcionalidad
            for feature_name, count in data.items():
                if feature_name == "last_used_by":
                    continue  # Ignorar el campo de usuario
                if feature_name not in usage_by_month[month]:
                    usage_by_month[month][feature_name] = 0
                usage_by_month[month][feature_name] += count

        # Paso 2: Calcular el rate de aumento mensual para cada funcionalidad
        increasing_rate = {}

        # Obtener los meses en orden cronológico
        sorted_months = sorted(usage_by_month.keys())

        for feature_name in usage_by_month[sorted_months[0]]:
            rates = []
            previous_count = 0
            for month in sorted_months:
                current_count = usage_by_month[month].get(feature_name, 0)
                if previous_count != 0:
                    rate = round((current_count - previous_count) / previous_count * 100,2)
                else:
                    rate = 0
                rates.append({month: rate})
                previous_count = current_count

            increasing_rate[feature_name] = rates

        return {"features_increasing_rate": increasing_rate}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el aumento de uso de funcionalidades: {str(e)}")

@app.get("/features-increasing-rate-daily")
def get_features_increasing_rate():
    try:
        features_ref = db.collection("feature_usage").stream()
        usage_by_day = {}

        # Paso 1: Agrupar los datos por día
        for feature in features_ref:
            data = feature.to_dict()
            doc_id = feature.id  # El nombre del documento es la fecha (YYYY-MM-DD)

            # Extraer el día del ID del documento
            try:
                day = datetime.strptime(doc_id, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                continue  # Ignorar si el ID no tiene el formato esperado

            # Inicializar el día en el diccionario si no existe
            if day not in usage_by_day:
                usage_by_day[day] = {}

            # Sumar los accesos por cada funcionalidad
            for feature_name, count in data.items():
                if feature_name == "last_used_by":
                    continue  # Ignorar el campo de usuario
                if feature_name not in usage_by_day[day]:
                    usage_by_day[day][feature_name] = 0
                usage_by_day[day][feature_name] += count

        # Paso 2: Calcular el rate de aumento diario para cada funcionalidad
        increasing_rate = {}

        # Obtener los días en orden cronológico
        sorted_days = sorted(usage_by_day.keys())

        for feature_name in usage_by_day[sorted_days[0]]:
            rates = []
            previous_count = None
            for day in sorted_days:
                current_count = usage_by_day[day].get(feature_name, 0)

                # Calcular el rate de aumento
                if previous_count is None:
                    rate = 0  # No hay día anterior, entonces el rate es 0
                elif previous_count == 0:
                    rate = 0
                else:
                    rate = round((current_count - previous_count) / previous_count * 100,2)

                rates.append({day: rate})
                previous_count = current_count

            increasing_rate[feature_name] = rates

        return {"features_increasing_rate": increasing_rate}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el aumento de uso de funcionalidades: {str(e)}")


@app.post("/analyticspages")
async def track_screen_time(data: ScreenTimeData):
    try:
        # Guarda los datos en Firestore
        doc_ref = db.collection("screen_times").document()
        doc_ref.set({
            "screen_name": data.screen_name,
            "duration": data.duration,
            "timestamp": data.timestamp,
        })
        return {"message": "Datos guardados exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))