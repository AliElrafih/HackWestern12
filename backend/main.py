import os
import io
from typing import List, Dict, Any
import sqlite3
import numpy as np
import cv2

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    print("Warning: DeepFace not available. Face recognition will be disabled.")
    DEEPFACE_AVAILABLE = False
    DeepFace = None

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles


# -------------------- FastAPI App --------------------
app = FastAPI()

app.mount("/faces", StaticFiles(directory="known_faces"), name="faces")

# -------------------- Config --------------------
DB_FILE = "hackathon_users.db"
KNOWN_FACES_DIR = "known_faces"
MODEL_NAME = "Facenet"

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

origins = [
    "http://localhost:5173",  # Vite
    "http://localhost:3000",  # CRA (if you ever use it)
]

# -------------------- CORS Middleware --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Global Variables --------------------
patient_embeddings: Dict[str, List[np.ndarray]] = {}
FAKE_PATIENT_DATA: Dict[str, Dict[str, Any]] = {
    "rad": {
        "patient_id": "1",
        "name": "Rad Mehdipour",
        "age": "35",
        "sex": "Male",
        "height": "6'0\"",
        "weight": "190 lbs",
        "insurance": "Aetna",
        "allergies": ["Peanuts", "Shellfish"],
        "conditions": ["Asthma"],
    },
    "ali": {
        "patient_id": "2",
        "name": "Ali El-Rafih",
        "age": "28",
        "sex": "Male",
        "height": "5'10\"",
        "weight": "175 lbs",
        "insurance": "BlueCross BlueShield",
        "allergies": ["Penicillin"],
        "conditions": ["Diabetes"],
    },
    "novak": {
        "patient_id": "3",
        "name": "Novak Vukojicic",
        "age": "42",
        "sex": "Female",
        "height": "5'6\"",
        "weight": "140 lbs",
        "insurance": "UnitedHealthcare",
        "allergies": [],
        "conditions": ["Hypertension"],
    },
    "akshin": {
        "patient_id": "4",
        "name": "Akshin Makkar",
        "age": "30",
        "sex": "Male",
        "height": "5'8\"",
        "weight": "165 lbs",
        "insurance": "Cigna",
        "allergies": ["Latex"],
        "conditions": ["High Cholesterol"],
    },
}


def load_saved_patients():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, age, sex, height, weight, insurance, allergies, conditions, profile_pic_path "
        "FROM users"
    )
    rows = cursor.fetchall()
    conn.close()

    
    for row in rows:
        # Use the first name (lowercased) as a key and ensure uniqueness
        key = row[1].split(' ')[0].lower()
        original_key = key
        suffix = 1
        while key in FAKE_PATIENT_DATA:
            key = f"{original_key}_{suffix}"
            suffix += 1

        FAKE_PATIENT_DATA[key] = {
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "sex": row[3],
            "height": row[4],
            "weight": row[5],
            "insurance": row[6],
            "allergies": row[7],
            "conditions": row[8],
            "profile_pic_path": row[9]
        }

    print("Loaded saved patients from database.")
    print(FAKE_PATIENT_DATA)

    

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

    if not DEEPFACE_AVAILABLE:
        print("DeepFace not available. Skipping face loading.")
        return

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
        "SELECT id, name, age, sex, height, weight, insurance, allergies, conditions, profile_pic_path "
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
            "insurance": row[6],
            "allergies": row[7],
            "conditions": row[8],
            "profile_pic_path": row[9]
        }
    return None

# -------------------- Startup Event --------------------
@app.on_event("startup")
def startup_event():
    load_saved_patients()
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
        "SELECT id, name, age, sex, height, weight, insurance, allergies, conditions, profile_pic_path "
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
            "insurance": row[6],
            "allergies": row[7],
            "conditions": row[8],
            "profile_pic_path": row[9]
        })
    return {"users": users}

@app.post("/add_user/")
async def add_user(
    name: str = Form(...),
    age: int = Form(None),
    sex: str = Form(None),
    height: str = Form(None),
    weight: str = Form(None),
    insurance: str = Form(None),
    allergies: str = Form(None),
    conditions: str = Form(None),
    profile_pic: UploadFile = File(None)
):
   # Read uploaded file once
    file_bytes = await profile_pic.read()

    # First copy
    pic_filename = f"{name.lower()}_1.jpg"
    pic_path = os.path.join(KNOWN_FACES_DIR, pic_filename)
    with open(pic_path, "wb") as f:
        f.write(file_bytes)

    # Second copy
    pic_filename2 = f"{name.lower()}_2.jpg"
    pic_path2 = os.path.join(KNOWN_FACES_DIR, pic_filename2)
    with open(pic_path2, "wb") as f:
        f.write(file_bytes)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, age, sex, height, weight, insurance, allergies, conditions, profile_pic_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, age, sex, height, weight, insurance, allergies, conditions, pic_filename)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"message": "User added", "user_id": user_id}

# -------------------- Face Recognition Endpoint --------------------
@app.post("/identify")
async def identify_patient(image: UploadFile = File(...)):
    # Mock mode when DeepFace is not available (for testing)
    if not DEEPFACE_AVAILABLE:
        # Return a mock successful match for testing
        # In production, this would require DeepFace
        import random
        mock_patients = ["ali", "rad", "novak"]
        mock_name = random.choice(mock_patients)
        patient_info = FAKE_PATIENT_DATA.get(mock_name, {})
        
        return {
            "match_found": True,
            "name": patient_info.get("name", mock_name.capitalize()),
            "similarity": 0.85,
            "confidence": 0.92,
            "patient_info": patient_info,
        }
    
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
        "name": patient_info.get("name", best_name),
        "similarity": best_score,
        "confidence": confidence,
        "patient_info": patient_info
    }
