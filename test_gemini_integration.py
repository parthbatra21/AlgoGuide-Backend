#!/usr/bin/env python3
"""
Test script for AlgoGuide Backend Gemini Integration
"""

import requests
import json
from typing import Dict, Any

# Base URL for your API (adjust if running on different host/port)
BASE_URL = "http://localhost:8000"

def test_store_user_answers():
    """Test storing user answers (prerequisite for resource generation)"""
    print("🧪 Testing user answer storage...")
    
    # Sample user answers based on your provided data
    test_answers = {
        "email": "test.user@example.com",
        "answers": [
            {
                "question_id": "onboarding_name",
                "question_text": "What is your name?",
                "answer": "Test User"
            },
            {
                "question_id": "onboarding_status",
                "question_text": "What is your current status?",
                "answer": "College Student"
            },
            {
                "question_id": "onboarding_education",
                "question_text": "What is your highest education level?",
                "answer": "B.Tech"
            },
            {
                "question_id": "onboarding_graduation_year",
                "question_text": "What is your year of graduation?",
                "answer": "2027"
            },
            {
                "question_id": "onboarding_primary_language",
                "question_text": "What is your primary programming language?",
                "answer": "Python"
            },
            {
                "question_id": "onboarding_tech_stack",
                "question_text": "Which technologies are in your tech stack?",
                "answer": "React, Node.js, FastAPI, Python"
            },
            {
                "question_id": "onboarding_familiar_topics",
                "question_text": "Which topics are you already familiar with?",
                "answer": "Basic Programming, Web Development"
            },
            {
                "question_id": "onboarding_weak_areas",
                "question_text": "Which areas are your weak points or you want to improve?",
                "answer": "DSA, System Design"
            },
            {
                "question_id": "onboarding_target_companies",
                "question_text": "Which companies are you targeting?",
                "answer": "Google, Microsoft, Amazon"
            },
            {
                "question_id": "onboarding_preferred_role",
                "question_text": "What is your preferred role?",
                "answer": "Software Developer"
            },
            {
                "question_id": "onboarding_target_timeline",
                "question_text": "What is your target timeline?",
                "answer": "6 months"
            },
            {
                "question_id": "onboarding_preferred_resources",
                "question_text": "What types of learning resources do you prefer?",
                "answer": "Video, Interactive Coding"
            }
        ]
    }
    
    try:
        # Store user answers
        response = requests.post(
            f"{BASE_URL}/users/{test_answers['email']}/answers",
            json=test_answers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User answers stored successfully!")
            print(f"   User ID: {result['user_id']}")
            print(f"   Total answers: {result['total_answers']}")
            return result['user_id']
        else:
            print(f"❌ Failed to store answers: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error. Make sure the server is running on http://localhost:8000")
        return None
    except Exception as e:
        print(f"❌ Error storing answers: {e}")
        return None

def test_generate_resources(user_id: str = None, email: str = None):
    """Test resource generation"""
    print("\n🤖 Testing resource generation with Gemini...")
    
    try:
        if user_id:
            url = f"{BASE_URL}/generate-resources/{user_id}"
        elif email:
            url = f"{BASE_URL}/generate-resources-by-email/{email}"
        else:
            print("❌ Need either user_id or email")
            return None
        
        print(f"   Sending request to: {url}")
        print("   This may take 30-60 seconds as Gemini analyzes and generates resources...")
        
        response = requests.post(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Resources generated successfully!")
            print(f"   Home Doc ID: {result['home_doc_id']}")
            print(f"   Total resources: {result['total_resources']}")
            print(f"   Categories: {', '.join(result['categories'])}")
            return result
        else:
            print(f"❌ Failed to generate resources: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error. Make sure the server is running on http://localhost:8000")
        return None
    except Exception as e:
        print(f"❌ Error generating resources: {e}")
        return None

def test_get_home_resources(user_id: str = None, email: str = None):
    """Test getting home resources"""
    print("\n📚 Testing home resource retrieval...")
    
    try:
        if user_id:
            url = f"{BASE_URL}/home/{user_id}"
        elif email:
            url = f"{BASE_URL}/home-by-email/{email}"
        else:
            print("❌ Need either user_id or email")
            return None
        
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Home resources retrieved successfully!")
            print(f"   User Profile: {result['user_profile']['name']}")
            print(f"   Total resources: {result['total_resources']}")
            
            # Show resource categories
            resources = result['resources']
            for category, items in resources.items():
                if items:  # Only show categories that have resources
                    print(f"   📂 {category.replace('_', ' ').title()}: {len(items)} resources")
                    for item in items[:2]:  # Show first 2 items
                        print(f"      • {item['title']}")
                    if len(items) > 2:
                        print(f"      ... and {len(items) - 2} more")
            
            return result
        else:
            print(f"❌ Failed to get home resources: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error. Make sure the server is running on http://localhost:8000")
        return None
    except Exception as e:
        print(f"❌ Error getting home resources: {e}")
        return None

def main():
    """Run all tests"""
    print("🚀 AlgoGuide Backend - Gemini Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Store user answers
    user_id = test_store_user_answers()
    if not user_id:
        print("❌ Cannot proceed without storing user answers first")
        return
    
    print(f"\n⏳ Waiting a moment before generating resources...")
    import time
    time.sleep(2)
    
    # Test 2: Generate resources
    generation_result = test_generate_resources(user_id=user_id)
    if not generation_result:
        print("❌ Resource generation failed")
        return
    
    print(f"\n⏳ Waiting a moment before retrieving resources...")
    time.sleep(2)
    
    # Test 3: Get home resources
    home_result = test_get_home_resources(user_id=user_id)
    if home_result:
        print("\n🎉 All tests passed successfully!")
    else:
        print("\n❌ Some tests failed")
    
    print("\n" + "=" * 60)
    print("📝 Next Steps:")
    print("1. Make sure you have set GEMINI_API_KEY environment variable")
    print("2. Check the 'home' collection in your Firebase console")
    print("3. Use the generated resources in your frontend application")

if __name__ == "__main__":
    main()