from collections import defaultdict
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field

class ScreenTimeData(BaseModel):
    screen_name: str
    duration: int
    timestamp: str

class CancellationTimeStats(BaseModel):
    hour: int
    total_cancellations: int
    percentage: float
    most_canceled_product: str
    example_cancellation_time: str


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

@app.get("/devices-summary")
def get_devices_summary():
    try:
        devices_ref = db.collection("userDevices").stream()
        model_counts = defaultdict(int)

        for doc in devices_ref:
            data = doc.to_dict()
            model = data.get("model", "Unknown")
            model_counts[model] += 1

        result = [{"model": model, "count": count} for model, count in model_counts.items()]
        result.sort(key=lambda x: x["count"], reverse=True)

        return {"device_model_distribution": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving device summary: {str(e)}")
    

@app.get("/top-products")
def obtener_top_productos():
    ordenes_ref = db.collection('product_orders')
    ordenes = ordenes_ref.stream()

    productos = defaultdict(int)

    for orden in ordenes:
        data = orden.to_dict()
        nombre = data.get("nameProduct", "Desconocido")
        cantidad = data.get("quantity", 0)

        # Asegurarse que cantidad sea numérico
        try:
            cantidad = int(cantidad)
        except:
            cantidad = 0

        productos[nombre] += cantidad

    # Convertir a lista y ordenar
    productos_ordenados = sorted(
        [{"nameProduct": k, "totalQuantity": v} for k, v in productos.items()],
        key=lambda x: x["totalQuantity"],
        reverse=True
    )

    return {"topProductos": productos_ordenados}
    


#Endpoint para devolver conteos totales de cada tipo de evento
@app.get("/analytics/detail-feature-usage")
async def get_detail_feature_usage():
    try:
        counts = {"order": 0, "directions": 0}
        for doc in db.collection("detail_events").stream():
            et = doc.to_dict().get("event_type")
            if et in counts:
                counts[et] += 1
        return counts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {e}")
    
@app.get("/analytics/most-liked-restaurants")
async def get_most_liked_restaurants():
    # Obtener las visitas a los restaurantes desde Firestore
    visitas_ref = db.collection('restaurant_visits')
    visitas = visitas_ref.stream()

    restaurantes_por_mes = defaultdict(lambda: defaultdict(int))  # {mes: {restaurante: visitas}}

    # Contar las visitas por mes y restaurante
    for visita in visitas:
        data = visita.to_dict()
        document_date = visita.id  # Usamos el ID del documento como la fecha (por ejemplo, "2025-04-26")
        
        # Extraer solo el mes y año (formato YYYY-MM)
        mes_anio = document_date[:7]  # "2025-04" (primeros 7 caracteres)

        for restaurant_name, visits in data.items():
            if restaurant_name != "last_visited_by":  # Ignorar el campo 'last_visited_by'
                try:
                    visitas_restaurante = int(visits)
                except ValueError:
                    visitas_restaurante = 0

                # Agregar al contador total de visitas por mes y restaurante
                restaurantes_por_mes[mes_anio][restaurant_name] += visitas_restaurante

    # Preparar la lista de resultados por mes
    resultados = []
    for mes_anio, restaurantes in restaurantes_por_mes.items():
        restaurantes_ordenados = sorted(
            [{"restaurantName": k, "totalVisits": v} for k, v in restaurantes.items()],
            key=lambda x: x["totalVisits"],
            reverse=True
        )
        resultados.append({"mes": mes_anio, "topRestaurantes": restaurantes_ordenados})

    return {"analytics": resultados}



@app.get("/analytics/orders-by-weekday")
def get_orders_by_weekday():
    try:
        orders_ref = db.collection("detail_events").where("event_type", "==", "order").stream()
        weekday_counts = defaultdict(int)

        for doc in orders_ref:
            data = doc.to_dict()
            timestamp = data.get("timestamp")
            if not timestamp:
                continue

            # Convert Firestore timestamp to Python datetime
            if isinstance(timestamp, datetime):
                dt = timestamp
            else:
                dt = timestamp.to_datetime()

            weekday = dt.strftime("%A")  # Monday, Tuesday, etc.
            weekday_counts[weekday] += 1

        # Opcional: ordenado por mayor cantidad
        sorted_counts = dict(sorted(weekday_counts.items(), key=lambda x: x[1], reverse=True))

        return {
            "orders_by_weekday": sorted_counts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/android-version-summary")
def get_android_version_summary():
    try:
        devices_ref = db.collection("userDevices").stream()
        version_counts = defaultdict(int)

        for doc in devices_ref:
            data = doc.to_dict()
            os_version = data.get("osVersion", "Unknown")
            version_counts[os_version] += 1

        result = [{"android_version": version, "count": count} for version, count in version_counts.items()]
        result.sort(key=lambda x: x["count"], reverse=True)

        return {"android_version_distribution": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving Android version summary: {str(e)}")
    

@app.get("/analytics/most-products-ordered")
async def get_most_products_ordered():
    # Obtener las visitas a los restaurantes desde Firestore
    visitas_ref = db.collection('orders_product')
    visitas = visitas_ref.stream()

    restaurantes_por_mes = defaultdict(lambda: defaultdict(int))  # {mes: {restaurante: visitas}}

    # Contar las visitas por mes y restaurante
    for visita in visitas:
        data = visita.to_dict()
        document_date = visita.id  # Usamos el ID del documento como la fecha (por ejemplo, "2025-04-26")
        
        # Extraer solo el mes y año (formato YYYY-MM)
        mes_anio = document_date[:7]  # "2025-04" (primeros 7 caracteres)

        for restaurant_name, visits in data.items():
            if restaurant_name != "last_visited_by":  # Ignorar el campo 'last_visited_by'
                try:
                    visitas_restaurante = int(visits)
                except ValueError:
                    visitas_restaurante = 0

                # Agregar al contador total de visitas por mes y restaurante
                restaurantes_por_mes[mes_anio][restaurant_name] += visitas_restaurante

    # Preparar la lista de resultados por mes
    resultados = []
    for mes_anio, restaurantes in restaurantes_por_mes.items():
        restaurantes_ordenados = sorted(
            [{"productName": k, "totalOrdered": v} for k, v in restaurantes.items()],
            key=lambda x: x["totalOrdered"],
            reverse=True
        )
        resultados.append({"mes": mes_anio, "topProductos": restaurantes_ordenados[:5]})

    return resultados
@app.get("/cancellation-time-stats", response_model=List[CancellationTimeStats])
async def get_cancellation_time_stats():
    """
    Analyzes at what time of day most order cancellations occur.
    Returns statistics grouped by hour of day.
    """
    # Calculate date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Initialize data structures
    hourly_stats = defaultdict(int)
    product_by_hour = defaultdict(lambda: defaultdict(int))
    example_times = {}
    
    # Get all users
    users_ref = db.collection('users')
    users = users_ref.stream()
    
    for user in users:
        # Get user's orders from the last month
        orders_ref = users_ref.document(user.id).collection('orders')
        orders_query = orders_ref.where('status', '==', 'cancelled').where('cancelledAt', '>=', start_date.isoformat())
        
        for order in orders_query.stream():
            order_data = order.to_dict()
            cancel_time_str = order_data.get('cancelledAt')
            
            if cancel_time_str:
                try:
                    # Parse cancellation time
                    cancel_time = datetime.fromisoformat(cancel_time_str.replace('Z', '+00:00'))
                    hour = cancel_time.hour
                    
                    # Update statistics
                    hourly_stats[hour] += 1
                    
                    # Track products by hour
                    product_name = order_data.get('productName', 'Unknown')
                    product_by_hour[hour][product_name] += 1
                    
                    # Store an example time for this hour
                    if hour not in example_times:
                        example_times[hour] = cancel_time.isoformat()
                        
                except ValueError as e:
                    print(f"Error parsing cancellation time {cancel_time_str}: {e}")
    
    # Calculate total cancellations
    total_cancellations = sum(hourly_stats.values())
    
    # Prepare response
    results = []
    for hour in sorted(hourly_stats.keys()):
        cancellations = hourly_stats[hour]
        
        # Find most canceled product for this hour
        most_canceled_product = max(
            product_by_hour[hour].items(), 
            key=lambda x: x[1]
        )[0] if product_by_hour[hour] else "No data"
        
        results.append({
            "hour": hour,
            "total_cancellations": cancellations,
            "percentage": (cancellations / total_cancellations * 100) if total_cancellations > 0 else 0,
            "most_canceled_product": most_canceled_product,
            "example_cancellation_time": example_times.get(hour, "")
        })
    
    return results