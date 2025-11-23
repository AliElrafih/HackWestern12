import os
import io
from typing import List, Dict, Any
import sqlite3
import numpy as np
import cv2
from deepface import DeepFace

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# -------------------- FastAPI App --------------------
app = FastAPI()

# -------------------- Config --------------------
DB_FILE = "hackathon_users.db"
PROFILE_PICS_DIR = "profile_pics"
KNOWN_FACES_DIR = "known_faces"
MODEL_NAME = "Facenet"

os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

# -------------------- CORS Middleware --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Global Variables --------------------
patient_embeddings: Dict[str, List[np.ndarray]] = {}
FAKE_PATIENT_DATA: Dict[str, Dict[str, Any]] = {
    "rad": {"patient_id": "A123", "allergies": ["Peanuts"], "conditions": ["Asthma"]},
    "ali": {"patient_id": "B456", "allergies": ["Penicillin"], "conditions": ["Diabetes"]},
    "novak": {"patient_id": "C789", "allergies": [], "conditions": ["Hypertension"]},
}

# -------------------- Helper Functions --------------------
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return -1.0
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))

def load_known_faces():
    global patient_embeddings
    patient_embeddings = {}

    if not os.path.exists(KNOWN_FACES_DIR):
        print(f"Known faces directory '{KNOWN_FACES_DIR}' does not exist.")
        return

    print("Loading known faces...")
    for filename in os.listdir(KNOWN_FACES_DIR):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue

        base_name = os.path.splitext(filename)[0].split("_")[0].lower()
        img_path = os.path.join(KNOWN_FACES_DIR, filename)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Failed to load image: {img_path}")
            continue

        try:
            reps = DeepFace.represent(img_path=img_path, model_name=MODEL_NAME, enforce_detection=True)
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            continue

        embedding = np.array(reps[0]["embedding"], dtype="float32")
        if base_name not in patient_embeddings:
            patient_embeddings[base_name] = []
        patient_embeddings[base_name].append(embedding)
        print(f"Loaded embedding for {base_name} from {filename}")

    print("Known faces loaded:")
    for name, embs in patient_embeddings.items():
        print(f"  {name}: {len(embs)} images")

def get_user_from_db(user_id: int) -> Dict:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, age, sex, height, weight, insurance_provider, insurance_policy, allergies, medical_history, profile_pic_path "
        "FROM users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "sex": row[3],
            "height": row[4],
            "weight": row[5],
            "insurance_provider": row[6],
            "insurance_policy": row[7],
            "allergies": row[8],
            "medical_history": row[9],
            "profile_pic_path": row[10]
        }
    return None

# -------------------- Startup Event --------------------
@app.on_event("startup")
def startup_event():
    load_known_faces()
    print(f"API ready with user DB and face recognition.")

# -------------------- Root Endpoint --------------------
@app.get("/")
def root():
    return {"message": "FastAPI running"}

# -------------------- User Endpoints --------------------
@app.get("/user/{user_id}")
def read_user(user_id: int):
    user = get_user_from_db(user_id)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/users/")
def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, age, sex, height, weight, insurance_provider, insurance_policy, allergies, medical_history, profile_pic_path "
        "FROM users"
    )
    rows = cursor.fetchall()
    conn.close()

    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "sex": row[3],
            "height": row[4],
            "weight": row[5],
            "insurance_provider": row[6],
            "insurance_policy": row[7],
            "allergies": row[8],
            "medical_history": row[9],
            "profile_pic_path": row[10]
        })
    return {"users": users}

@app.post("/add_user/")
async def add_user(
    name: str = Form(...),
    age: int = Form(...),
    sex: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    insurance_provider: str = Form(...),
    insurance_policy: str = Form(...),
    allergies: str = Form(...),
    medical_history: str = Form(...),
    profile_pic: UploadFile = File(...)
):
    pic_filename = f"{name}_{profile_pic.filename}"
    pic_path = os.path.join(PROFILE_PICS_DIR, pic_filename)
    with open(pic_path, "wb") as f:
        f.write(await profile_pic.read())

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, age, sex, height, weight, insurance_provider, insurance_policy, allergies, medical_history, profile_pic_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, age, sex, height, weight, insurance_provider, insurance_policy, allergies, medical_history, pic_path)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"message": "User added", "user_id": user_id}

# -------------------- Face Recognition Endpoint --------------------
@app.post("/identify")
async def identify_patient(image: UploadFile = File(...)):
    image_data = await image.read()
    np_arr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"match_found": False, "reason": "Could not decode image"}

    try:
        reps = DeepFace.represent(img_path=img, model_name=MODEL_NAME, enforce_detection=True)
    except Exception as e:
        return {"match_found": False, "reason": f"Face representation error: {e}"}

    query_emb = np.array(reps[0]["embedding"], dtype="float32")
    if not patient_embeddings:
        return {"match_found": False, "reason": "No known faces loaded. Add images to known_faces/ and restart."}

    best_name = None
    best_score = -1.0
    for name, embeddings in patient_embeddings.items():
        scores = [cosine_similarity(query_emb, emb) for emb in embeddings]
        person_best = max(scores)
        if person_best > best_score:
            best_score = person_best
            best_name = name

    THRESHOLD = 0.3
    if best_name is None or best_score < THRESHOLD:
        return {"match_found": False, "reason": "No good match", "best_candidate": best_name, "similarity": best_score}

    confidence = (best_score + 1) / 2.0
    patient_info = FAKE_PATIENT_DATA.get(best_name.lower(), {})

    return {
        "match_found": True,
        "name": best_name,
        "similarity": best_score,
        "confidence": confidence,
        "patient_info": patient_info
    }
