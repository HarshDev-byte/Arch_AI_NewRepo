#!/usr/bin/env python3
"""
Test the ArchAI API endpoints
"""
import requests
import json

def test_api():
    """Test the API endpoints"""
    base_url = "http://localhost:8000"
    
    try:
        # Test projects endpoint
        print("🧪 Testing /api/projects endpoint...")
        response = requests.get(f"{base_url}/api/projects")
        
        if response.status_code == 200:
            projects = response.json()
            print(f"✅ Found {len(projects)} projects:")
            for project in projects:
                print(f"   - {project['name']} ({project['status']})")
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            
        # Test health endpoint
        print("\n🧪 Testing /health endpoint...")
        response = requests.get(f"{base_url}/health")
        
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Health check: {health}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server. Is it running on port 8000?")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_api()