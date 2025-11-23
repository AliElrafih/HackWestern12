import os
import io
from typing import List, Dict, Any

import numpy as np
import cv2

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    print("Warning: DeepFace not available. Face recognition will be disabled.")
    DEEPFACE_AVAILABLE = False
    DeepFace = None

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

# Allow frontend (e.g., React on localhost:3000) to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in real life, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

KNOWN_FACES_DIR = "known_faces"
MODEL_NAME = "Facenet"

known_embeddings: List[np.ndarray] = []
known_names: List[str] = []

FAKE_PATIENT_DATA: Dict[str, Dict[str, Any]] = {
    "rad": {
        "patient_id": "A123",
        "name": "Rad Smith",
        "age": "35",
        "sex": "Male",
        "height": "6'0\"",
        "weight": "190 lbs",
        "insurance": "Aetna",
        "allergies": ["Peanuts", "Shellfish"],
        "conditions": ["Asthma"],
    },
    "ali": {
        "patient_id": "B456",
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
        "patient_id": "C789",
        "name": "Novak Johnson",
        "age": "42",
        "sex": "Female",
        "height": "5'6\"",
        "weight": "140 lbs",
        "insurance": "UnitedHealthcare",
        "allergies": [],
        "conditions": ["Hypertension"],
    },
}

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return -1.0
    
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    
    return float(np.dot(a,b) / (a_norm * b_norm))

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

        name_with_suffix = os.path.splitext(filename)[0]  # e.g. "rad_1"
        base_name = name_with_suffix.split("_")[0].lower()  # "rad_1" -> "rad"

        img_path = os.path.join(KNOWN_FACES_DIR, filename)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Failed to load image: {img_path}")
            continue

        try:
            reps = DeepFace.represent(
                img_path=img_path,
                model_name=MODEL_NAME,
                enforce_detection=True
            )
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            continue

        embedding = np.array(reps[0]["embedding"], dtype="float32")

        # add embedding to this person's list
        if base_name not in patient_embeddings:
            patient_embeddings[base_name] = []
        patient_embeddings[base_name].append(embedding)

        print(f"Loaded embedding for {base_name} from {filename}")

    print("Summary loaded:")
    for name, embs in patient_embeddings.items():
        print(f"  {name}: {len(embs)} images")

@app.get("/")
def root():
    return {"message": "FastAPI running"}


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
        reps = DeepFace.represent(
            img_path=img,
            model_name=MODEL_NAME,
            enforce_detection=True
        )
    except Exception as e:
        return {"match_found": False, "reason": f"Face representation error: {e}"}
    
    query_emb = np.array(reps[0]["embedding"], dtype="float32")

    if not patient_embeddings:
        return {
            "match_found": False,
            "reason": "No known faces loaded. Add images to known_faces/ and restart.",
        }

    best_name = None
    best_score = -1.0

    # go through each person and all their photos
    for name, embeddings in patient_embeddings.items():
        scores = [cosine_similarity(query_emb, emb) for emb in embeddings]
        person_best = max(scores)
        print(f"{name}: scores={scores}, best={person_best}")

        if person_best > best_score:
            best_score = person_best
            best_name = name

    THRESHOLD = 0.3  # tuned for hackathon

    if best_name is None or best_score < THRESHOLD:
        return {
            "match_found": False,
            "reason": "No good match",
            "best_candidate": best_name,
            "similarity": best_score,
        }

    # map similarity [-1,1] -> [0,1] for nicer "confidence"
    confidence = (best_score + 1) / 2.0

    patient_info = FAKE_PATIENT_DATA.get(best_name.lower(), {})

    return {
        "match_found": True,
        "name": patient_info.get("name", best_name),
        "similarity": best_score,
        "confidence": confidence,
        "patient_info": patient_info,
    }



@app.on_event("startup")
def startup_event():
    load_known_faces()
    print(f"Loaded {len(known_names)} known faces:", known_names)
