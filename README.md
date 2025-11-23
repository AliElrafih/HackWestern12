# Identicare - Patient Identification System

A face recognition system for patient identification in healthcare settings, built with FastAPI backend and React frontend.

## Features

- 🖼️ Image upload and face recognition
- 👤 Patient identification using DeepFace
- 📋 Patient information display (allergies, conditions, patient ID)
- 🎨 Modern, responsive UI

## Project Structure

```
HackWestern12/
├── backend/          # FastAPI backend
│   ├── main.py      # Main API server
│   └── known_faces/ # Reference face images
└── frontend/        # React frontend
```

## Setup

### Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install fastapi uvicorn deepface opencv-python numpy tensorflow
```

4. Run the backend server:
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the port shown in the terminal)

## Usage

1. Start the backend server (port 8000)
2. Start the frontend development server
3. Open the frontend URL in your browser
4. Upload a patient photo
5. Click "Identify Patient" to see the results

## API Endpoints

- `GET /` - Health check
- `POST /identify` - Upload an image and identify the patient

## Technologies

- **Backend**: FastAPI, DeepFace, OpenCV, NumPy
- **Frontend**: React, Vite
- **AI/ML**: DeepFace for face recognition

