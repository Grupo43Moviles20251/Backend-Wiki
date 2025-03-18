import datetime
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
        # 🔥 Verificar si el usuario YA EXISTE en Firebase Auth
        try:
            firebase_user = auth.get_user_by_email(user.email)  
            user_id = firebase_user.uid  
            print(f"Usuario {user.email} ya existe en Firebase Auth con UID: {user_id}")
        except auth.UserNotFoundError:
            print(f"Usuario {user.email} NO encontrado en Firebase Auth. Creándolo...")
            firebase_user = auth.create_user(
                email=user.email,
                password=user.password
            )
            user_id = firebase_user.uid  # Obtenemos el nuevo UID

        # Guardar datos del usuario en Firestore
        user_data = {
            "name": user.name,
            "email": user.email,
            "address": user.address,
            "birthday": user.birthday,
            "created_at": datetime.datetime.now()
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





# 📌 Ruta para agregar un nuevo restaurante
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

# 📌 Ruta para actualizar la disponibilidad del restaurante
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
