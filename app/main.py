from datetime import datetime
import uuid
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi import security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, firestore, auth
from pydantic import BaseModel
from streamlit import _event
from typing import List


# Inicializar FastAPI
app = FastAPI()
security =  HTTPBearer()
# Cargar credenciales de Firebase
cred = credentials.Certificate("./serviceAccountKey.json")

firebase_admin.initialize_app(cred)

# Cliente Firestore
db = firestore.client()

# Modelo Pydantic para un usuario
class User(BaseModel):
    name: str
    email: str
    password: str
    address: str
    birthday: str
    
class Product(BaseModel):
    productId: int
    productName: str
    amount: int
    available: bool
    discountPrice: float
    originalPrice: float
    

class Restaurant(BaseModel):
    name: str
    imageUrl: str
    description: str
    latitude: float
    longitude: float
    address: str
    products: List[Product]
    rating: float
    type: int


class OrderRequest(BaseModel):
    product_id: int
    quantity: int

    
# Verificar el token de autenticación
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token")



# Ruta para registro (Sign Up)
from firebase_admin import auth, firestore

@app.post("/signup")
def signup(user: User):
    try:
        # Verificar si el usuario YA EXISTE en Firebase Auth
        try:
            firebase_user = auth.get_user_by_email(user.email)
            user_id = firebase_user.uid
            print(f"Usuario {user.email} ya existe en Firebase Auth con UID: {user_id}")
            
            # Lanzar error explícito
            raise HTTPException(status_code=409, detail="Este correo ya está registrado.")
        
        except auth.UserNotFoundError:
            print(f"Usuario {user.email} NO encontrado en Firebase Auth. Creándolo...")
            firebase_user = auth.create_user(
                email=user.email,
                password=user.password
            )
            user_id = firebase_user.uid  # Nuevo UID

        # Guardar datos del usuario en Firestore
        user_data = {
            "name": user.name,
            "email": user.email,
            "address": user.address,
            "birthday": user.birthday,
            "created_at": datetime.now(),
        }
        db.collection('users').document(user_id).set(user_data)

        return {"message": "User created successfully", "uid": user_id}

    except Exception as e:
        print(f"⚠ Error en el registro: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Ruta para obtener datos del usuario (Log In)
@app.get("/users/me")
def get_user_data(user: dict = Depends(get_current_user)):
    user_id = user["uid"]
    print(f"Buscando usuario en Firestore con UID: {user_id}")
    
    doc_ref = db.collection('users').document(user_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"Usuario con UID {user_id} no encontrado en Firestore")
        raise HTTPException(status_code=404, detail="User not found") 

    return doc.to_dict()


# Crear un nuevo usuario
@app.post("/users/{user_id}")
def create_user(user_id: str, user: User):
    doc_ref = db.collection('users').document(user_id)
    doc_ref.set(user.dict())
    _event("user_created", {"user_id": user_id})
    return {"message": "User created successfully"}

# Obtener datos de un usuario
@app.get("/users/{user_id}")
def get_user(user_id: str):
    doc = db.collection('users').document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    _event("user_fetched", {"user_id": user_id})
    return doc.to_dict()

# Actualizar un usuario
@app.put("/users/{user_id}")
def update_user(user_id: str, user: User):
    doc_ref = db.collection('users').document(user_id)
    doc_ref.update(user.dict())
    _event("user_updated", {"user_id": user_id})
    return {"message": "User updated successfully"}

# Eliminar un usuario
@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    doc_ref = db.collection('users').document(user_id)
    doc_ref.delete()
    _event("user_deleted", {"user_id": user_id})
    return {"message": "User deleted successfully"}


# Ruta para obtener todos los restaurantes
@app.get("/restaurants", response_model=List[Restaurant])
def get_restaurants():
    try:
        # Obtener todos los documentos de la colección `restaurants`
        restaurants_ref = db.collection("retaurants").stream()
        restaurants = []

        # Mostrar la cantidad de documentos obtenidos
        docs = list(restaurants_ref)
        
        # Recorrer los documentos y agregar los detalles a la lista
        for doc in docs:
            restaurant_data = doc.to_dict()

            # Verificar si los campos esenciales existen
            if 'name' in restaurant_data and 'products' in restaurant_data:
                restaurant_data["id"] = doc.id  # Agregar el id del documento al restaurante
                restaurants.append(restaurant_data)

        return restaurants
    
    except Exception as e:
        print(f"Error al obtener restaurantes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Ruta para obtener un restaurante por tipo
@app.get("/restaurants/type/{type}", response_model=List[Restaurant])
def get_restaurants_by_type(type: int):
    try:
        # Obtener todos los documentos de la colección `restaurants` donde el campo `type` sea igual al parámetro `type`
        restaurants_ref = db.collection("retaurants").where("type", "==", type).stream()
        restaurants = []

        # Recorrer los documentos y agregar los detalles a la lista
        for doc in restaurants_ref:
            restaurant_data = doc.to_dict()

            # Verificar si los campos esenciales existen
            if 'name' in restaurant_data and 'products' in restaurant_data:
                restaurant_data["id"] = doc.id  # Agregar el id del documento al restaurante
                restaurants.append(restaurant_data)

        return restaurants
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ruta para buscar restaurantes por nombre o productos
@app.get("/restaurants/search/{query}", response_model=List[Restaurant])
def search_restaurants(query: str):
    try:
        # Normalizar el query eliminando espacios y convirtiendo a minúsculas, luego separar en palabras
        query_normalized = query.strip().lower().replace(" ", "")
        query_words = query_normalized.split()

        # Obtener todos los restaurantes de la colección
        restaurants_ref = db.collection("retaurants").stream()
        
        restaurants = []

        # Recorrer todos los restaurantes para aplicar la búsqueda
        for doc in restaurants_ref:
            restaurant_data = doc.to_dict()

            # Normalizar el nombre del restaurante
            restaurant_name_normalized = restaurant_data.get("name", "").strip().lower().replace(" ", "")

            # Verificar si alguna de las palabras de la búsqueda está en el nombre del restaurante
            if any(word in restaurant_name_normalized for word in query_words):
                restaurant_data["id"] = doc.id  # Agregar el id del restaurante
                if restaurant_data not in restaurants:
                    restaurants.append(restaurant_data)

            # Verificar dentro de los productos
            if 'products' in restaurant_data:
                for product in restaurant_data['products']:
                    # Normalizar el nombre del producto
                    product_name_normalized = product.get("productName", "").strip().lower()

                    # Verificar si alguna de las palabras de la búsqueda está en el nombre del producto
                    if any(word in product_name_normalized for word in query_words):
                        if restaurant_data not in restaurants:
                            restaurant_data["id"] = doc.id  # Agregar el id del restaurante
                            restaurants.append(restaurant_data)

        return restaurants
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/products/{product_id}")
def get_product_by_id(product_id: int):
    try:
        # Obtener todos los documentos de la colección restaurants
        restaurants_ref = db.collection("retaurants").stream()
        

        # Recorrer los documentos y buscar el producto por ID
        for doc in restaurants_ref:
            restaurant_data = doc.to_dict()
            if 'products' in restaurant_data:
                for product in restaurant_data['products']:
                    if product['productId'] == product_id:
                        product['restaurantId'] = doc.id  # Agregar el id del restaurante al producto
                        products = restaurant_data

        if not products:
            raise HTTPException(status_code=404, detail="Product not found")

        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Ruta para agregar un nuevo restaurante
@app.post("/restaurants", response_model=dict)
def create_restaurant(restaurant: Restaurant, user: dict = Depends(get_current_user)):
    try:
        # Verificar si el producto está disponible (si la cantidad > 0)
        if restaurant.products[0].amount <= 0:
            raise HTTPException(status_code=400, detail="Product is out of stock")

        new_restaurant_ref = db.collection("restaurants").add(restaurant.dict())
        return {"message": "Restaurant added successfully", "id": new_restaurant_ref[1].id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ruta para actualizar la disponibilidad del restaurante
@app.put("/restaurants/{restaurant_id}", response_model=dict)
def update_restaurant(restaurant_id: str, restaurant: Restaurant, user: dict = Depends(get_current_user)):
    try:
        restaurant_ref = db.collection("restaurants").document(restaurant_id)
        restaurant_ref.update(restaurant.dict())
        
        # Actualizar el estado de disponibilidad basado en la cantidad
        if restaurant.products[0].amount == 0:
            restaurant_ref.update({"available": False})
        
        return {"message": "Restaurant updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/order")
def order_product(request: OrderRequest):
    product_id = request.product_id
    quantity = request.quantity

    restaurants_ref = db.collection('retaurants')


    # Buscar restaurante con ese productId (dado que solo hay 1 producto por restaurante)
    query = (doc for doc in restaurants_ref.stream() if doc.to_dict()['products'][0]['productId'] == product_id)
    doc = next(query, None)
    

    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")

    restaurant_data = doc.to_dict()
    product = restaurant_data['products'][0]

    if not product.get("available", False):
        raise HTTPException(status_code=400, detail="Product not available")

    if product.get("amount", 0) < quantity:
        raise HTTPException(status_code=400, detail="Not enough quantity available")

    # Actualizar la cantidad
    new_amount = product["amount"] - quantity
    doc_ref = restaurants_ref.document(doc.id)
    doc_ref.update({
        "products": [{
            **product,
            "amount": new_amount
        }]
    })


    # Generar código de reclamo
    claim_code = str(uuid.uuid4())[:8].upper()

    return {
        "message": "Order placed successfully",
        "code": claim_code,
        "product_name": product.get("productName"),
        "quantity_ordered": quantity,
        "restaurant": restaurant_data.get("name"),
    }

    
# @app.get("/order/{restaurant_name}/decrease-stock")
# def decrease_product_stock_by_name(restaurant_name: str, product_name: str, price: float):
#     try:
#         # FastAPI ya convierte %20 a espacio, por lo tanto:
#         # restaurant_name podría ser "La Trattoria"
#         cleaned_input_name = restaurant_name.replace(" ", "").lower()

#         # Obtener todos los restaurantes
#         docs = db.collection("retaurants").get()

#         # Buscar el documento cuyo nombre (sin espacios) coincida
#         matching_doc = next(
#             (doc for doc in docs if doc.to_dict().get("name", "").replace(" ", "").lower() == cleaned_input_name),
#             None
#         )

#         if not matching_doc:
#             raise HTTPException(status_code=404, detail="Restaurante no encontrado")

#         restaurant_ref = matching_doc.reference
#         restaurant_data = matching_doc.to_dict()
#         products = restaurant_data.get("products", [])

#         if not products:
#             raise HTTPException(status_code=400, detail="El restaurante no tiene productos")

#         product = products[0]

#         if product["amount"] <= 0:
#             raise HTTPException(status_code=400, detail="El producto ya no tiene stock")

#         # Disminuir el stock
#         product["amount"] -= 1

#         if product["amount"] == 0:
#             product["available"] = False

#         # Guardar los cambios
#         restaurant_ref.update({"products": [product]})

#         order_id = str(uuid4())[:9].upper()

#         return {
#             "order_id": order_id
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/order/{restaurant_name}/decrease-stock/{product_name}/{price}/{u_id}")
def decrease_product_stock_by_name(
        restaurant_name: str,
        product_name: str,
        price: float,
        u_id: str
):
    try:
        cleaned_input_name = restaurant_name.replace(" ", "").lower()

        # ➊ Encontrar el restaurante
        docs = db.collection("retaurants").get()
        matching_doc = next(
            (doc for doc in docs
             if doc.to_dict().get("name", "").replace(" ", "").lower() == cleaned_input_name),
            None
        )
        if not matching_doc:
            raise HTTPException(status_code=404, detail="Restaurante no encontrado")

        restaurant_ref = matching_doc.reference
        restaurant_data = matching_doc.to_dict()
        products = restaurant_data.get("products", [])
        if not products:
            raise HTTPException(status_code=400, detail="El restaurante no tiene productos")

        product = products[0]
        if product["amount"] <= 0:
            raise HTTPException(status_code=400, detail="El producto ya no tiene stock")

        # ➋ Disminuir stock (SIN CAMBIOS)
        product["amount"] -= 1
        if product["amount"] == 0:
            product["available"] = False
        restaurant_ref.update({"products": [product]})

        # ➌ Crear el ID de la orden
        order_id = str(uuid4())[:8].upper()

        # ➍ Registrar la orden bajo el usuario ---------------------------------
        uid = u_id
        order_data = {
            "order_id": order_id,
            "product_name": product_name,
            "price": price,
            "state": "pending",
            "date": datetime.now().strftime("%d/%m/%Y/%H:%M")
        }

        user_orders_ref = db.collection("orders").document(uid)
        doc = user_orders_ref.get()
        if doc.exists:
            # Añadir sin duplicar con ArrayUnion
            user_orders_ref.update({
                "orders": firestore.ArrayUnion([order_data])
            })
        else:
            # Crear el documento con la primera orden
            user_orders_ref.set({
                "orders": [order_data]
            })
        # ---------------------------------------------------------------------

        # ➎ Respuesta (SIN CAMBIOS)
        return {"order_id": order_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/orders/{user_id}")
def get_orders_by_user(user_id: str):
    try:
        user_orders_ref = db.collection("orders").document(user_id)
        doc = user_orders_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Usuario no tiene órdenes o no existe")

        data = doc.to_dict()
        orders = data.get("orders", [])
        return {"user_id": user_id, "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.put("/orders/{user_id}/cancel/{order_id}")
def cancel_order(user_id: str, order_id: str):
    try:
        user_orders_ref = db.collection("orders").document(user_id)
        doc = user_orders_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Usuario no tiene órdenes o no existe")

        data = doc.to_dict()
        orders = data.get("orders", [])

        # Buscar la orden por order_id
        order_found = False
        for order in orders:
            if order.get("order_id") == order_id:
                if order.get("state") == "cancelled":
                    raise HTTPException(status_code=400, detail="La orden ya está cancelada")
                order["state"] = "cancelled"
                order_found = True
                break

        if not order_found:
            raise HTTPException(status_code=404, detail="Orden no encontrada")

        # Actualizar la lista completa con el cambio
        user_orders_ref.update({"orders": orders})

        return {"message": f"Orden {order_id} cancelada correctamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
