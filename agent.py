import os
import json
import asyncio
import aiohttp
from typing import List, Dict, Any
import google.generativeai as genai
from bs4 import BeautifulSoup
import re
from datetime import datetime
import firebase_admin
from firebase_admin import firestore

class GeminiWebAgent:
    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini Web Agent
        
        Args:
            api_key (str): Gemini API key. If not provided, will try to get from environment variable GEMINI_API_KEY
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or pass it to constructor.")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Search engines and resources
        self.search_engines = [
            "https://www.google.com/search?q=",
            "https://www.bing.com/search?q=",
        ]
        
        # Resource domains to prioritize
        self.resource_domains = [
            "youtube.com",
            "medium.com", 
            "dev.to",
            "stackoverflow.com",
            "github.com",
            "geeksforgeeks.org",
            "leetcode.com",
            "hackerrank.com",
            "coursera.org",
            "udemy.com",
            "freecodecamp.org",
            "w3schools.com",
            "tutorialspoint.com",
            "javatpoint.com"
        ]

    async def analyze_user_profile(self, user_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze user's onboarding answers to create a learning profile
        
        Args:
            user_answers: List of question-answer pairs from user onboarding
            
        Returns:
            Dict containing analyzed profile and search queries
        """
        # Extract key information from answers
        profile = {
            "name": "",
            "status": "",
            "education": "",
            "graduation_year": "",
            "primary_language": "",
            "tech_stack": [],
            "familiar_topics": [],
            "weak_areas": [],
            "target_companies": [],
            "preferred_role": "",
            "target_timeline": "",
            "preferred_resources": []
        }
        
        for answer in user_answers:
            question_id = answer.get("question_id", "")
            answer_text = answer.get("answer", "")
            
            if "name" in question_id:
                profile["name"] = answer_text
            elif "status" in question_id:
                profile["status"] = answer_text
            elif "education" in question_id:
                profile["education"] = answer_text
            elif "graduation_year" in question_id:
                profile["graduation_year"] = answer_text
            elif "primary_language" in question_id:
                profile["primary_language"] = answer_text
            elif "tech_stack" in question_id:
                profile["tech_stack"] = [tech.strip() for tech in answer_text.split(',')]
            elif "familiar_topics" in question_id:
                profile["familiar_topics"] = [topic.strip() for topic in answer_text.split(',')]
            elif "weak_areas" in question_id:
                profile["weak_areas"] = [area.strip() for area in answer_text.split(',')]
            elif "target_companies" in question_id:
                profile["target_companies"] = [company.strip() for company in answer_text.split(',')]
            elif "preferred_role" in question_id:
                profile["preferred_role"] = answer_text
            elif "target_timeline" in question_id:
                profile["target_timeline"] = answer_text
            elif "preferred_resources" in question_id:
                profile["preferred_resources"] = [resource.strip() for resource in answer_text.split(',')]
        
        # Generate search queries using Gemini
        search_queries = await self.generate_search_queries(profile)
        
        return {
            "profile": profile,
            "search_queries": search_queries
        }

    async def generate_search_queries(self, profile: Dict[str, Any]) -> List[str]:
        """
        Use Gemini to generate relevant search queries based on user profile
        
        Args:
            profile: User profile dictionary
            
        Returns:
            List of search queries
        """
        prompt = f"""
        Based on this user profile, generate 10-15 specific search queries to find the best learning resources:
        
        Name: {profile['name']}
        Status: {profile['status']}
        Education: {profile['education']}
        Primary Language: {profile['primary_language']}
        Tech Stack: {', '.join(profile['tech_stack'])}
        Familiar Topics: {', '.join(profile['familiar_topics'])}
        Weak Areas: {', '.join(profile['weak_areas'])}
        Target Companies: {', '.join(profile['target_companies'])}
        Preferred Role: {profile['preferred_role']}
        Timeline: {profile['target_timeline']}
        Preferred Resources: {', '.join(profile['preferred_resources'])}
        
        Generate search queries that will help find:
        1. Learning resources for weak areas
        2. Interview preparation materials for target companies
        3. Skill development content for preferred role
        4. Practice problems and exercises
        5. Technology-specific tutorials
        
        Return only the search queries, one per line, without numbering or extra text.
        Focus on actionable, specific queries that will yield good learning resources.
        """
        
        try:
            response = self.model.generate_content(prompt)
            queries = [q.strip() for q in response.text.split('\n') if q.strip()]
            return queries[:15]  # Limit to 15 queries
        except Exception as e:
            print(f"Error generating search queries: {e}")
            # Fallback queries based on profile
            fallback_queries = []
            
            for weak_area in profile['weak_areas']:
                fallback_queries.append(f"{weak_area} tutorial {profile['primary_language']}")
                fallback_queries.append(f"{weak_area} interview questions")
            
            for company in profile['target_companies']:
                fallback_queries.append(f"{company} {profile['preferred_role']} interview preparation")
            
            for tech in profile['tech_stack']:
                fallback_queries.append(f"{tech} best practices tutorial")
            
            return fallback_queries[:15]

    async def search_and_scrape(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for resources and scrape content
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of scraped resource data
        """
        resources = []
        
        try:
            # Use Gemini to search and get URLs (simulated web search)
            search_prompt = f"""
            For the search query: "{query}"
            
            Provide a list of 5-10 high-quality URLs that would contain valuable learning resources for this topic.
            Focus on:
            - YouTube tutorials
            - Blog posts on Medium, Dev.to
            - GitHub repositories
            - LeetCode/HackerRank problems
            - Documentation and tutorials
            - Course platforms (Coursera, Udemy)
            
            Return only URLs, one per line, without any additional text or formatting.
            Make sure the URLs are realistic and would likely contain the requested content.
            """
            
            response = self.model.generate_content(search_prompt)
            urls = [url.strip() for url in response.text.split('\n') if url.strip() and url.startswith('http')]
            
            # For each URL, create resource metadata using Gemini
            for url in urls[:max_results]:
                resource = await self.create_resource_metadata(url, query)
                if resource:
                    resources.append(resource)
                    
        except Exception as e:
            print(f"Error searching for query '{query}': {e}")
            # Create fallback resource
            resources.append({
                "title": f"Learning Resource: {query}",
                "url": f"https://www.google.com/search?q={query.replace(' ', '+')}",
                "description": f"Search results for {query}",
                "resource_type": "search",
                "difficulty": "beginner",
                "tags": query.split(),
                "created_at": datetime.utcnow().isoformat()
            })
        
        return resources

    async def create_resource_metadata(self, url: str, query: str) -> Dict[str, Any]:
        """
        Create resource metadata using Gemini analysis
        
        Args:
            url: Resource URL
            query: Original search query
            
        Returns:
            Resource metadata dictionary
        """
        try:
            # Use Gemini to analyze the URL and create metadata
            analysis_prompt = f"""
            Analyze this URL and create metadata for a learning resource: {url}
            Original search query: {query}
            
            Based on the URL structure and domain, provide:
            1. A descriptive title (max 100 chars)
            2. A helpful description (max 300 chars)
            3. Resource type (video, blog, course, documentation, practice, repository)
            4. Difficulty level (beginner, intermediate, advanced)
            5. Estimated time to complete (in minutes)
            6. Key topics/tags (comma-separated)
            
            Format as JSON:
            {{
                "title": "...",
                "description": "...",
                "resource_type": "...",
                "difficulty": "...",
                "estimated_time": 30,
                "tags": ["tag1", "tag2", "tag3"]
            }}
            """
            
            response = self.model.generate_content(analysis_prompt)
            
            # Try to parse JSON response
            try:
                import json
                metadata = json.loads(response.text)
            except:
                # Fallback metadata if JSON parsing fails
                domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
                metadata = {
                    "title": f"{query} - {domain}",
                    "description": f"Learning resource about {query} from {domain}",
                    "resource_type": "unknown",
                    "difficulty": "intermediate",
                    "estimated_time": 30,
                    "tags": query.split()
                }
            
            # Add additional fields
            metadata.update({
                "url": url,
                "query": query,
                "created_at": datetime.utcnow().isoformat(),
                "source": "gemini_web_agent"
            })
            
            return metadata
            
        except Exception as e:
            print(f"Error creating metadata for {url}: {e}")
            return None

    async def process_user_and_generate_resources(self, user_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main method to process user answers and generate personalized resources
        
        Args:
            user_answers: List of user's onboarding answers
            
        Returns:
            Dictionary containing all generated resources and metadata
        """
        # Analyze user profile
        analysis = await self.analyze_user_profile(user_answers)
        profile = analysis["profile"]
        search_queries = analysis["search_queries"]
        
        # Search and collect resources for each query
        all_resources = []
        
        for query in search_queries:
            print(f"Searching for: {query}")
            resources = await self.search_and_scrape(query, max_results=3)
            all_resources.extend(resources)
            
            # Add small delay to avoid overwhelming the API
            await asyncio.sleep(0.5)
        
        # Categorize resources using Gemini
        categorized_resources = await self.categorize_resources(all_resources, profile)
        
        return {
            "user_profile": profile,
            "search_queries": search_queries,
            "total_resources": len(all_resources),
            "resources": categorized_resources,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def categorize_resources(self, resources: List[Dict[str, Any]], profile: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize resources based on user profile and content
        
        Args:
            resources: List of all resources
            profile: User profile
            
        Returns:
            Categorized resources dictionary
        """
        categories = {
            "weak_areas_improvement": [],
            "interview_preparation": [],
            "skill_development": [],
            "practice_problems": [],
            "technology_tutorials": [],
            "general_learning": []
        }
        
        try:
            # Use Gemini to categorize resources
            categorization_prompt = f"""
            Categorize these resources based on the user profile:
            
            User Profile:
            - Weak Areas: {', '.join(profile['weak_areas'])}
            - Target Companies: {', '.join(profile['target_companies'])}
            - Preferred Role: {profile['preferred_role']}
            - Tech Stack: {', '.join(profile['tech_stack'])}
            
            Resources to categorize:
            {json.dumps([{'title': r['title'], 'description': r['description'], 'tags': r.get('tags', [])} for r in resources], indent=2)}
            
            Assign each resource to one of these categories:
            - weak_areas_improvement: Resources that help with user's weak areas
            - interview_preparation: Resources for interview prep, especially for target companies
            - skill_development: Resources for developing skills for preferred role
            - practice_problems: Coding problems, exercises, challenges
            - technology_tutorials: Tutorials for specific technologies in tech stack
            - general_learning: Other valuable learning resources
            
            Return as JSON mapping resource titles to categories:
            {{
                "Resource Title 1": "category_name",
                "Resource Title 2": "category_name"
            }}
            """
            
            response = self.model.generate_content(categorization_prompt)
            
            try:
                import json
                categorization = json.loads(response.text)
            except:
                # Fallback: categorize based on keywords
                categorization = {}
                for resource in resources:
                    title = resource['title']
                    if any(weak in title.lower() for weak in profile['weak_areas']):
                        categorization[title] = "weak_areas_improvement"
                    elif any(company.lower() in title.lower() for company in profile['target_companies']):
                        categorization[title] = "interview_preparation"
                    elif "practice" in title.lower() or "problem" in title.lower():
                        categorization[title] = "practice_problems"
                    elif any(tech.lower() in title.lower() for tech in profile['tech_stack']):
                        categorization[title] = "technology_tutorials"
                    else:
                        categorization[title] = "general_learning"
            
            # Assign resources to categories
            for resource in resources:
                category = categorization.get(resource['title'], 'general_learning')
                if category in categories:
                    categories[category].append(resource)
                else:
                    categories['general_learning'].append(resource)
                    
        except Exception as e:
            print(f"Error categorizing resources: {e}")
            # Fallback: put all resources in general_learning
            categories['general_learning'] = resources
        
        return categories

# Singleton instance
gemini_agent = None

def get_gemini_agent(api_key: str = None) -> GeminiWebAgent:
    """Get or create a Gemini agent instance"""
    global gemini_agent
    if gemini_agent is None:
        gemini_agent = GeminiWebAgent(api_key)
    return gemini_agent

async def generate_personalized_resources(user_answers: List[Dict[str, Any]], db: firestore.Client, user_id: str) -> Dict[str, Any]:
    """
    Main function to generate and save personalized resources
    
    Args:
        user_answers: User's onboarding answers
        db: Firestore database client
        user_id: User ID for saving resources
        
    Returns:
        Generated resources data
    """
    try:
        # Get Gemini agent
        agent = get_gemini_agent()
        
        # Generate resources
        resources_data = await agent.process_user_and_generate_resources(user_answers)
        
        # Save to Firebase under 'home' collection
        home_doc_data = {
            "user_id": user_id,
            "user_profile": resources_data["user_profile"],
            "search_queries": resources_data["search_queries"],
            "total_resources": resources_data["total_resources"],
            "resources": resources_data["resources"],
            "generated_at": resources_data["generated_at"],
            "created_at": firestore.SERVER_TIMESTAMP
        }
        
        # Save to home collection
        home_ref = db.collection('home').add(home_doc_data)
        home_doc_id = home_ref[1].id
        
        # Add home document ID to response
        resources_data["home_doc_id"] = home_doc_id
        
        return resources_data
        
    except Exception as e:
        print(f"Error generating personalized resources: {e}")
        raise e
