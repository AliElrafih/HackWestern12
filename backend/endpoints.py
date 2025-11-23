from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import Response
from pydantic import BaseModel
import sqlite3
from typing import Dict
import os

app = FastAPI()

DB_FILE = "hackathon_users.db"
PROFILE_PICS_DIR = "profile_pics"

os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

# ------------------- User Info Endpoint -------------------
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
    else:
        return None

@app.get("/user/{user_id}")
def read_user(user_id: int):
    user = get_user_from_db(user_id)
    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")

# ------------------- Add User Endpoint (auto ID) -------------------
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
    
    cursor.execute("""
        INSERT INTO users (name, age, sex, height, weight, insurance_provider, insurance_policy, allergies, medical_history, profile_pic_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, age, sex, height, weight, insurance_provider, insurance_policy, allergies, medical_history, pic_path))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"message": "User added", "user_id": user_id}

# ------------------- Get All Users Endpoint -------------------
@app.get("/users/")
def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, age, sex, height, weight, insurance_provider, insurance_policy, allergies, medical_history, profile_pic_path
        FROM users
    """)
    
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