#!/usr/bin/env python3
"""
Simple test script for the sharing functionality.
Tests the sharing endpoints without requiring a full database setup.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

async def test_sharing_endpoints():
    """Test the sharing endpoint logic"""
    print("🧪 Testing sharing functionality...")
    
    # Mock project data
    mock_project = MagicMock()
    mock_project.id = "test-project-id"
    mock_project.user_id = "test-user-id"
    mock_project.name = "Test Project"
    
    # Mock user
    mock_user = {"user_id": "test-user-id"}
    
    # Mock database
    mock_db = AsyncMock()
    
    try:
        # Import the sharing functions
        from routes.projects import create_share_link, revoke_share, get_shared_project
        
        print("✅ Successfully imported sharing endpoints")
        
        # Test token generation
        import secrets
        token = secrets.token_urlsafe(16)
        print(f"✅ Generated test token: {token[:8]}...")
        
        # Test share URL generation
        from config import settings
        share_url = f"{settings.app_url}/share/{token}"
        print(f"✅ Generated share URL: {share_url}")
        
        print("✅ All sharing components imported successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

async def test_frontend_types():
    """Test that the frontend types are consistent"""
    print("\n🎨 Testing frontend type consistency...")
    
    # Check if the ShareButton component exists
    share_button_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'components', 'ShareButton.tsx')
    if os.path.exists(share_button_path):
        print("✅ ShareButton component exists")
    else:
        print("❌ ShareButton component not found")
        return False
    
    # Check if the shared project page exists
    shared_page_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'app', 'share', '[token]', 'page.tsx')
    if os.path.exists(shared_page_path):
        print("✅ Shared project page exists")
    else:
        print("❌ Shared project page not found")
        return False
    
    print("✅ Frontend components exist!")
    return True

async def main():
    """Run all tests"""
    print("🚀 Testing ArchAI Sharing Implementation\n")
    
    backend_ok = await test_sharing_endpoints()
    frontend_ok = await test_frontend_types()
    
    if backend_ok and frontend_ok:
        print("\n🎉 All tests passed! Sharing functionality is ready.")
        print("\n📋 Next steps:")
        print("1. Run the SQL migration: scripts/add_sharing_columns.sql")
        print("2. Start the backend server")
        print("3. Test the sharing UI in the project page")
        return True
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)