from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import urllib.parse
from dotenv import load_dotenv
from agent import generate_personalized_resources

# Load environment variables from .env file
load_dotenv()

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

# CORS configuration to allow browser preflight (OPTIONS) requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to your frontend origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
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

class ResourceGenerationRequest(BaseModel):
    user_id: str
    email: str

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

@app.post("/generate-resources/{user_id}")
async def generate_resources_endpoint(user_id: str):
    """
    Generate personalized learning resources for a user based on their onboarding answers
    """
    try:
        # Get user's latest onboarding answers
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get the latest question answers (get all and sort in Python to avoid index requirement)
        answers_ref = db.collection('users').document(user_id).collection('question_answers')
        answers_docs = list(answers_ref.stream())
        
        if not answers_docs:
            raise HTTPException(status_code=404, detail="No onboarding answers found for this user")
        
        # Sort by submitted_at in Python to get the latest
        try:
            answers_docs.sort(key=lambda x: x.to_dict().get('submitted_at', 0), reverse=True)
        except:
            # If sorting fails, just use the first document
            pass
        
        # Get the answers from the latest submission
        latest_answers = answers_docs[0].to_dict()
        user_answers = latest_answers.get('answers', [])
        
        if not user_answers:
            raise HTTPException(status_code=400, detail="No answers found in the latest submission")
        
        # Generate personalized resources using Gemini
        resources_data = await generate_personalized_resources(user_answers, db, user_id)
        
        return {
            "message": "Personalized resources generated successfully",
            "user_id": user_id,
            "home_doc_id": resources_data["home_doc_id"],
            "total_resources": resources_data["total_resources"],
            "categories": list(resources_data["resources"].keys()),
            "generated_at": resources_data["generated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating resources: {str(e)}")

@app.post("/generate-resources-by-email/{email}")
async def generate_resources_by_email_endpoint(email: str):
    """
    Generate personalized learning resources for a user by email
    """
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
        
        # Get the latest question answers (get all and sort in Python to avoid index requirement)
        answers_ref = db.collection('users').document(user_id).collection('question_answers')
        answers_docs = list(answers_ref.stream())
        
        if not answers_docs:
            raise HTTPException(status_code=404, detail="No onboarding answers found for this user")
        
        # Sort by submitted_at in Python to get the latest
        try:
            answers_docs.sort(key=lambda x: x.to_dict().get('submitted_at', 0), reverse=True)
        except:
            # If sorting fails, just use the first document
            pass
        
        # Get the answers from the latest submission
        latest_answers = answers_docs[0].to_dict()
        user_answers = latest_answers.get('answers', [])
        
        if not user_answers:
            raise HTTPException(status_code=400, detail="No answers found in the latest submission")
        
        # Generate personalized resources using Gemini
        resources_data = await generate_personalized_resources(user_answers, db, user_id)
        
        return {
            "message": "Personalized resources generated successfully",
            "email": decoded_email,
            "user_id": user_id,
            "home_doc_id": resources_data["home_doc_id"],
            "total_resources": resources_data["total_resources"],
            "categories": list(resources_data["resources"].keys()),
            "generated_at": resources_data["generated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating resources: {str(e)}")

@app.get("/home/{user_id}")
async def get_user_home_resources(user_id: str):
    """
    Get all generated home resources for a user
    """
    try:
        # Get all home documents for this user (without ordering to avoid index requirement)
        home_ref = db.collection('home')
        query = home_ref.where('user_id', '==', user_id)
        home_docs = list(query.stream())
        
        if not home_docs:
            raise HTTPException(status_code=404, detail="No resources found for this user")
        
        # Sort by created_at in Python instead of Firestore to avoid index requirement
        home_docs_with_data = []
        for doc in home_docs:
            doc_data = doc.to_dict()
            doc_data['home_doc_id'] = doc.id
            home_docs_with_data.append(doc_data)
        
        # Sort by created_at (most recent first)
        try:
            home_docs_with_data.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        except:
            # If sorting fails, just return the first document
            pass
        
        # Return the latest resources
        return home_docs_with_data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching home resources: {str(e)}")

@app.get("/home-by-email/{email}")
async def get_user_home_resources_by_email(email: str):
    """
    Get all generated home resources for a user by email
    """
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
        
        # Get all home documents for this user (without ordering to avoid index requirement)
        home_ref = db.collection('home')
        query = home_ref.where('user_id', '==', user_id)
        home_docs = list(query.stream())
        
        if not home_docs:
            raise HTTPException(status_code=404, detail="No resources found for this user")
        
        # Sort by created_at in Python instead of Firestore to avoid index requirement
        home_docs_with_data = []
        for doc in home_docs:
            doc_data = doc.to_dict()
            doc_data['home_doc_id'] = doc.id
            home_docs_with_data.append(doc_data)
        
        # Sort by created_at (most recent first)
        try:
            home_docs_with_data.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        except:
            # If sorting fails, just return the first document
            pass
        
        # Return the latest resources
        home_data = home_docs_with_data[0]
        home_data['email'] = decoded_email
        
        return home_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching home resources: {str(e)}")

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port_env = os.getenv("PORT")
    try:
        port = int(port_env) if port_env else 8000
    except ValueError:
        port = 8000

    try:
        uvicorn.run(app, host=host, port=port)
    except OSError as e:
        # macOS errno 48, Linux errno 98 => address already in use
        if getattr(e, "errno", None) in (48, 98):
            for candidate in range(port + 1, port + 6):
                try:
                    print(f"Port {port} busy. Trying {candidate}...")
                    uvicorn.run(app, host=host, port=candidate)
                    break
                except OSError as e2:
                    if getattr(e2, "errno", None) in (48, 98):
                        continue
                    raise
        else:
            raise
