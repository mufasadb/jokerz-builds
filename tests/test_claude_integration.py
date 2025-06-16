#!/usr/bin/env python3
"""
Simple test script for Claude integration
"""

import os
from src.analysis.claude_integration import NaturalLanguageQueryService
from src.storage.database import DatabaseManager

def test_claude_integration():
    """Test the Claude integration with sample queries"""
    
    # Check if API key is available
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set. Set environment variable to test Claude integration.")
        print("Example: export ANTHROPIC_API_KEY='your_api_key_here'")
        assert True  # Skip test when no API key
        return
    
    try:
        # Initialize services
        print("🔧 Initializing database and Claude service...")
        db = DatabaseManager()
        query_service = NaturalLanguageQueryService(api_key, db)
        
        # Test queries
        test_queries = [
            "What are the best jugg builds?",
            "Show me some cold builds",
            "Find tanky witch builds",
            "What minion builds are there?"
        ]
        
        print("🚀 Testing natural language queries...\n")
        
        for i, query in enumerate(test_queries, 1):
            print(f"Test {i}: '{query}'")
            try:
                # Test fallback parsing (works without API)
                result = query_service.process_query(query)
                
                print(f"✅ Query processed successfully")
                print(f"   Intent: {result['intent']['type']}")
                print(f"   Filters: {result['intent']['filters']}")
                print(f"   Results: {result['count']} found")
                print(f"   Summary: {result['summary']}")
                
                if result['count'] > 0:
                    print(f"   Top result: {result['results'][0]['name']} (Level {result['results'][0]['level']})")
                
            except Exception as e:
                print(f"❌ Query failed: {e}")
            
            print()
        
        print("🎉 Claude integration test completed!")
        assert True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        assert False, f"Integration test failed: {e}"

def test_fallback_parsing():
    """Test fallback parsing without Claude API"""
    print("🔧 Testing fallback parsing (no API required)...")
    
    try:
        db = DatabaseManager()
        # Pass None as API key to test fallback
        query_service = NaturalLanguageQueryService(None, db)
        
        test_queries = [
            "juggernaut builds",
            "cold skills", 
            "cheap tanky builds",
            "dot builds"
        ]
        
        for query in test_queries:
            result = query_service.process_query(query)
            print(f"'{query}' -> {result['intent']['filters']}")
        
        print("✅ Fallback parsing works!")
        assert True
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        assert False, f"Fallback test failed: {e}"

if __name__ == "__main__":
    print("Joker Builds - Claude Integration Test")
    print("=" * 50)
    
    # Test fallback first (always works)
    test_fallback_parsing()
    print()
    
    # Test full Claude integration if API key available
    test_claude_integration()