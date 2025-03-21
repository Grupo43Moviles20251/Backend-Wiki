import firebase_admin
from firebase_admin import credentials, firestore


cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

import datetime
today = datetime.date.today().strftime("%Y-%m-%d")

doc_ref = db.collection("feature_usage").document(today)
doc = doc_ref.get()

if doc.exists:
    data = doc.to_dict()
    sorted_features = sorted(data.items(), key=lambda x: x[1]) 
    print("📉 Feature menos usada:", sorted_features[0])
else:
    print("No hay datos de hoy.")