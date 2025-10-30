from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import urllib.parse

# Initialize Firebase
def initialize_firebase():
    if not firebase_admin._apps:
        # For development, you can use the service account key file
        # In production, use environment variables or other secure methods
        cred_path = "firebase-credentials.json"
        
        # Check if we have valid credentials
        if os.path.exists(cred_path):
            try:
                # Read and validate the credentials file
                with open(cred_path, 'r') as f:
                    import json
                    cred_data = json.load(f)
                    
                # Check if it's a placeholder file
                if ("YOUR_PRIVATE_KEY_HERE" in str(cred_data.get('private_key', '')) or 
                    "YOUR_PRIVATE_KEY_ID_HERE" in str(cred_data.get('private_key_id', ''))):
                    print("Warning: firebase-credentials.json contains placeholder values.")
                    print("Using Firebase emulator mode for development.")
                    # Use emulator or mock mode
                    os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
                    firebase_admin.initialize_app()
                else:
                    # Valid credentials file
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"Error reading credentials file: {e}")
                print("Using Firebase emulator mode for development.")
                os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
                firebase_admin.initialize_app()
        else:
            # No credentials file found
            print("No firebase-credentials.json found. Using Firebase emulator mode.")
            os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
            firebase_admin.initialize_app()
    
    return firestore.client()

# Initialize Firestore
db = initialize_firebase()

# Create FastAPI instance
app = FastAPI(
    title="AlgoGuide Backend API",
    description="A simple backend application with Firebase integration",
    version="1.0.0"
)

# Pydantic models
class User(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    age: Optional[int] = None

class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

class QuestionAnswer(BaseModel):
    question_id: str
    question_text: str
    answer: str

class UserAnswers(BaseModel):
    email: str
    answers: List[QuestionAnswer]

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to AlgoGuide Backend API with Firebase", "status": "running"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "database": "Firebase Firestore"}

# User endpoints
@app.get("/users", response_model=List[User])
async def get_users():
    try:
        users_ref = db.collection('users')
        users = []
        for doc in users_ref.stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            users.append(user_data)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        if not user.exists:
            raise HTTPException(status_code=404, detail="User not found")
        user_data = user.to_dict()
        user_data['id'] = user.id
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")

@app.post("/users")
async def create_user(user: UserCreate):
    try:
        user_data = {
            "name": user.name,
            "email": user.email,
            "age": user.age
        }
        doc_ref = db.collection('users').add(user_data)
        user_data['id'] = doc_ref[1].id
        return user_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.put("/users/{user_id}")
async def update_user(user_id: str, user: UserCreate):
    try:
        user_ref = db.collection('users').document(user_id)
        if not user_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = {
            "name": user.name,
            "email": user.email,
            "age": user.age
        }
        user_ref.update(user_data)
        user_data['id'] = user_id
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    try:
        user_ref = db.collection('users').document(user_id)
        if not user_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_ref.delete()
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

@app.post("/users/{email}/answers")
async def store_user_answers(email: str, user_answers: UserAnswers):
    try:
        # Decode URL-encoded email
        decoded_email = urllib.parse.unquote(email)
        
        # First, check if the user exists by querying the users collection by email
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', decoded_email).limit(1)
        users = list(query.stream())
        
        if not users:
            # User doesn't exist, create a new user automatically
            new_user_data = {
                "name": decoded_email.split('@')[0].title(),  # Use email prefix as name
                "email": decoded_email,
                "age": None
            }
            doc_ref = db.collection('users').add(new_user_data)
            user_id = doc_ref[1].id
            user_created = True
        else:
            user_doc = users[0]
            user_id = user_doc.id
            user_created = False
        
        # Prepare the answers data
        answers_data = {
            "email": user_answers.email,
            "answers": [
                {
                    "question_id": answer.question_id,
                    "question_text": answer.question_text,
                    "answer": answer.answer
                }
                for answer in user_answers.answers
            ],
            "submitted_at": firestore.SERVER_TIMESTAMP
        }
        
        # Store answers in a subcollection under the user document
        answers_ref = db.collection('users').document(user_id).collection('question_answers').add(answers_data)
        
        return {
            "message": "User answers stored successfully",
            "email": decoded_email,
            "user_id": user_id,
            "user_created": user_created,
            "answers_id": answers_ref[1].id,
            "total_answers": len(user_answers.answers)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing user answers: {str(e)}")

@app.get("/users/{email}/answers")
async def get_user_answers(email: str):
    try:
        # Decode URL-encoded email
        decoded_email = urllib.parse.unquote(email)
        
        # Find the user by email
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', decoded_email).limit(1)
        users = list(query.stream())
        
        if not users:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_doc = users[0]
        user_id = user_doc.id
        
        # Get all answer submissions for this user
        answers_ref = db.collection('users').document(user_id).collection('question_answers')
        answer_submissions = []
        
        for doc in answers_ref.stream():
            submission_data = doc.to_dict()
            submission_data['submission_id'] = doc.id
            answer_submissions.append(submission_data)
        
        return {
            "email": decoded_email,
            "user_id": user_id,
            "submissions": answer_submissions,
            "total_submissions": len(answer_submissions)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user answers: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
