from datetime import datetime
import uuid
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

@app.post("/order/{restaurant_id}/decrease-stock")
def decrease_product_stock(restaurant_id: str):
    try:
        restaurant_ref = db.collection("retaurants").document(restaurant_id)
        restaurant_doc = restaurant_ref.get()

        if not restaurant_doc.exists:
            raise HTTPException(status_code=404, detail="Restaurante no encontrado")

        restaurant_data = restaurant_doc.to_dict()
        products = restaurant_data.get("products", [])

        if not products:
            raise HTTPException(status_code=400, detail="El restaurante no tiene productos")

        # Solo trabajamos con el primer producto como mencionaste
        product = products[0]

        if product["amount"] <= 0:
            raise HTTPException(status_code=400, detail="El producto ya no tiene stock")

        # Disminuir en 1 el stock
        product["amount"] -= 1

        # Cambiar a no disponible si el stock llegó a 0
        if product["amount"] == 0:
            product["available"] = False

        # Guardar cambios en Firestore
        restaurant_ref.update({"products": [product]})

        return {
            "message": "Stock actualizado correctamente",
            "new_amount": product["amount"],
            "available": product["available"],
            "product_name": product["productName"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
