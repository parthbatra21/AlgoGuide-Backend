# AlgoGuide Backend - Gemini Web Integration

This backend service integrates Google's Gemini AI to analyze user onboarding data and generate personalized learning resources by scraping information across the internet.

## Features

- 🤖 **Gemini AI Integration**: Uses Google's Gemini API to analyze user profiles and generate search queries
- 🌐 **Web Scraping**: Intelligently searches for learning resources across the web
- 📚 **Resource Categorization**: Automatically categorizes resources based on user needs
- 🔥 **Firebase Integration**: Stores generated resources in Firestore
- 🚀 **FastAPI**: RESTful API endpoints for easy integration
- 📊 **Personalized Learning**: Tailored resources based on user's weak areas, target companies, and learning preferences

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Set the environment variable:

```bash
# On Windows
set GEMINI_API_KEY=your_api_key_here

# On Linux/Mac
export GEMINI_API_KEY=your_api_key_here
```

Or create a `.env` file (copy from `.env.example`):
```
GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Set up Firebase

Make sure your `firebase-credentials.json` file is properly configured with your Firebase service account credentials.

### 4. Run the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Generate Resources

Generate personalized learning resources for a user:

**By User ID:**
```http
POST /generate-resources/{user_id}
```

**By Email:**
```http
POST /generate-resources-by-email/{email}
```

### Get Home Resources

Retrieve generated resources for a user:

**By User ID:**
```http
GET /home/{user_id}
```

**By Email:**
```http
GET /home-by-email/{email}
```

## How It Works

1. **User Analysis**: The Gemini agent analyzes the user's onboarding answers to create a learning profile
2. **Query Generation**: Gemini generates targeted search queries based on:
   - Weak areas to improve
   - Target companies for interview prep
   - Preferred technologies and roles
   - Learning timeline and preferences
3. **Resource Discovery**: The system searches for high-quality resources from:
   - YouTube tutorials
   - Technical blogs (Medium, Dev.to)
   - GitHub repositories
   - Coding practice platforms (LeetCode, HackerRank)
   - Course platforms (Coursera, Udemy)
4. **Categorization**: Resources are automatically categorized:
   - 📈 **Weak Areas Improvement**
   - 💼 **Interview Preparation**
   - 🛠️ **Skill Development**
   - 💻 **Practice Problems**
   - 📖 **Technology Tutorials**
   - 🎓 **General Learning**
5. **Storage**: All resources are saved to Firebase under the `home` collection

## Data Structure

### User Profile (from onboarding)
```json
{
  "name": "User Name",
  "status": "College Student",
  "education": "B.Tech",
  "graduation_year": "2027",
  "primary_language": "Python",
  "tech_stack": ["React", "Node.js", "FastAPI"],
  "familiar_topics": ["Web Development"],
  "weak_areas": ["DSA", "System Design"],
  "target_companies": ["Google", "Microsoft"],
  "preferred_role": "Software Developer",
  "target_timeline": "6 months",
  "preferred_resources": ["Video", "Interactive Coding"]
}
```

### Generated Resources
```json
{
  "user_id": "user123",
  "user_profile": { /* user profile data */ },
  "search_queries": [
    "DSA tutorial Python beginner",
    "Google software engineer interview preparation",
    "System design basics course"
  ],
  "total_resources": 25,
  "resources": {
    "weak_areas_improvement": [
      {
        "title": "Data Structures and Algorithms in Python",
        "url": "https://example.com/dsa-python",
        "description": "Comprehensive DSA course for beginners",
        "resource_type": "course",
        "difficulty": "beginner",
        "estimated_time": 120,
        "tags": ["DSA", "Python", "Algorithms"]
      }
    ],
    "interview_preparation": [ /* ... */ ],
    /* ... other categories ... */
  },
  "generated_at": "2025-10-31T00:04:08Z"
}
```

## Testing

Run the test script to verify the integration:

```bash
python test_gemini_integration.py
```

This will:
1. Store sample user answers
2. Generate personalized resources
3. Retrieve and display the results

## Environment Variables

- `GEMINI_API_KEY`: Required for Gemini AI integration
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

## Firebase Collections

- `users`: User profiles and basic information
- `users/{uid}/question_answers`: User onboarding responses
- `home`: Generated personalized resources for each user

## Error Handling

The system includes comprehensive error handling:
- Fallback queries if Gemini API fails
- Graceful degradation for resource categorization
- Detailed error messages in API responses

## Rate Limiting

The system includes built-in delays to respect API rate limits:
- 0.5 second delay between search queries
- Configurable batch sizes for resource generation

## Security Notes

- Never commit API keys to version control
- Use environment variables or secure key management
- Restrict CORS origins in production
- Validate all user inputs

## Production Deployment

1. Set up proper environment variables
2. Configure CORS origins for your frontend
3. Use a production WSGI server (gunicorn, uvicorn)
4. Set up proper Firebase security rules
5. Monitor API usage and costs