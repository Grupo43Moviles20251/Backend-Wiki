import datetime
from fastapi import Depends, FastAPI, HTTPException
from fastapi import security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, firestore, auth
from pydantic import BaseModel
from streamlit import _event

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
