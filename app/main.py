from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, firestore, analytics
from pydantic import BaseModel
from streamlit import _event

# Inicializar FastAPI
app = FastAPI()

# Cargar credenciales de Firebase
cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Cliente Firestore
db = firestore.client()

# Modelo Pydantic para un usuario
class User(BaseModel):
    name: str
    email: str

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
