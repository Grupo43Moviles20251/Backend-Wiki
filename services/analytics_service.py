from collections import defaultdict
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

        # Paso 2: Calcular el rate de aumento mensual para cada pantalla
        increasing_rate = {}

        # Obtener los meses en orden cronológico
        sorted_months = sorted(usage_by_month.keys())

        # Calcular la tasa de aumento para cada vista
        for month in sorted_months:
            for feature_name, count in usage_by_month[month].items():
                if feature_name == "last_used_by":
                    continue  # Ignorar el campo de usuario
                if feature_name not in increasing_rate:
                    increasing_rate[feature_name] = []

                # Obtenemos el count del mes anterior si existe
                previous_count = 0
                if sorted_months.index(month) > 0:
                    previous_month = sorted_months[sorted_months.index(month) - 1]
                    previous_count = usage_by_month[previous_month].get(feature_name, 0)

                # Calculamos el rate
                if previous_count != 0:
                    rate = round((count - previous_count) / previous_count * 100, 2)
                else:
                    rate = 0

                # Añadimos al resultado el rate y la fecha
                increasing_rate[feature_name].append({month: rate})

        # Reorganizar el JSON como se pide, con la fecha como clave y rate de cada view
        result = {}
        for feature_name, rates in increasing_rate.items():
            for rate in rates:
                for month, value in rate.items():
                    if month not in result:
                        result[month] = {}
                    result[month][feature_name] = value

        return {"features_increasing_rate": result}

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

        # Paso 2: Calcular el rate de aumento diario para cada vista
        increasing_rate = {}

        # Obtener los días en orden cronológico
        sorted_days = sorted(usage_by_day.keys())

        # Calcular la tasa de aumento para cada vista
        for day in sorted_days:
            for feature_name, count in usage_by_day[day].items():
                if feature_name == "last_used_by":
                    continue  # Ignorar el campo de usuario
                if feature_name not in increasing_rate:
                    increasing_rate[feature_name] = []

                # Obtenemos el count del día anterior si existe
                previous_count = 0
                if sorted_days.index(day) > 0:
                    previous_day = sorted_days[sorted_days.index(day) - 1]
                    previous_count = usage_by_day[previous_day].get(feature_name, 0)

                # Calculamos el rate de aumento
                if previous_count != 0:
                    rate = round((count - previous_count) / previous_count * 100, 2)
                else:
                    rate = 0

                # Añadimos al resultado el rate y la fecha
                increasing_rate[feature_name].append({day: rate})

        # Reorganizar el JSON como se pide, con la fecha como clave y rate de cada view
        result = {}
        for feature_name, rates in increasing_rate.items():
            for rate in rates:
                for day, value in rate.items():
                    if day not in result:
                        result[day] = {}
                    result[day][feature_name] = value

        return {"features_increasing_rate": result}

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

@app.get("/screen-analytics")
async def get_screen_analytics():
    try:
        screen_times_ref = db.collection("screen_times")
        docs = screen_times_ref.stream()

        
        screen_data = defaultdict(lambda: defaultdict(lambda: {"total_duration": 0, "session_count": 0}))

        
        for doc in docs:
            data = doc.to_dict()
            screen_name = data["screen_name"]
            duration = data["duration"]
            timestamp = data["timestamp"]  # Asegúrate de que este campo exista en tus documentos

            # Convertir el timestamp a una hora del día (0-23)
            hour = datetime.fromisoformat(timestamp).hour
            

            # Sumar el tiempo total y aumentar el conteo de sesiones por pantalla y por hora
            screen_data[screen_name][hour]["total_duration"] += duration
            screen_data[screen_name][hour]["session_count"] += 1

        # Calcular el tiempo promedio por pantalla y por hora
        analytics = []
        for screen_name, hours_data in screen_data.items():
            screen_analytics = {
                "screen_name": screen_name,
                "hourly_analytics": []
            }
            for hour, stats in hours_data.items():
                avg_duration = stats["total_duration"] / stats["session_count"]
                screen_analytics["hourly_analytics"].append({
                    "hour": hour,
                    "total_duration": stats["total_duration"],
                    "session_count": stats["session_count"],
                    "avg_duration": avg_duration,
                })
            # Ordenar por hora
            screen_analytics["hourly_analytics"].sort(key=lambda x: x["hour"])
            analytics.append(screen_analytics)

        # Ordenar por tiempo total descendente
        analytics.sort(key=lambda x: sum(h["total_duration"] for h in x["hourly_analytics"]), reverse=True)

        return {"analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/average-time-spent")
async def get_average_time_spent():
    try:
        # Obtén los datos de la colección de tiempos de pantalla
        screen_times_ref = db.collection("screen_times")
        docs = screen_times_ref.stream()

        # Inicializa un diccionario para almacenar la duración total y la cantidad de sesiones por pantalla
        screen_data = defaultdict(lambda: {"total_duration": 0, "session_count": 0})

        # Procesa los documentos para sumar la duración por pantalla
        for doc in docs:
            data = doc.to_dict()
            screen_name = data["screen_name"]
            duration = data["duration"]

            # Suma la duración total y aumenta el contador de sesiones para cada pantalla
            if screen_name == "HomePage" or screen_name == "SearchPage":
                screen_data[screen_name]["total_duration"] += duration
                screen_data[screen_name]["session_count"] += 1

        # Calcula el tiempo promedio por pantalla
        average_time_spent = []
        for screen_name, data in screen_data.items():
            if data["session_count"] > 0:
                avg_duration = data["total_duration"] / data["session_count"]
                average_time_spent.append({
                    "screen_name": screen_name,
                    "average_duration": avg_duration,
                    "session_count": data["session_count"],
                })

        return {"average_time_spent": average_time_spent}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
