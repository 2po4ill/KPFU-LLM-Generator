"""
Quick test script for RPD API endpoints
Run with: python test_rpd_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_submit_rpd_data():
    """Test submitting RPD data and getting fingerprint"""
    
    rpd_data = {
        "subject_title": "Программирование на Python",
        "academic_degree": "bachelor",
        "profession": "Прикладная информатика",
        "total_hours": 144,
        "department": "Кафедра информационных технологий",
        "lecture_themes": [
            {
                "title": "Введение в Python",
                "order": 1,
                "hours": 4,
                "description": "Основы языка Python"
            },
            {
                "title": "Структуры данных",
                "order": 2,
                "hours": 6,
                "description": "Списки, словари, множества"
            }
        ],
        "literature_references": [
            {
                "authors": "Лутц М.",
                "title": "Изучаем Python",
                "year": 2019,
                "publisher": "O'Reilly"
            }
        ]
    }
    
    print("Testing /rpd/submit-data endpoint...")
    response = requests.post(f"{BASE_URL}/rpd/submit-data", json=rpd_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success! Fingerprint: {result.get('rpd_id')}")
        print(f"  Message: {result.get('message')}")
        print(f"  Warnings: {result.get('warnings', [])}")
        return result.get('rpd_id')
    else:
        print(f"✗ Failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return None


def test_retrieve_content(fingerprint):
    """Test retrieving content by fingerprint"""
    
    print(f"\nTesting /rpd/retrieve-content/{fingerprint} endpoint...")
    response = requests.get(f"{BASE_URL}/rpd/retrieve-content/{fingerprint}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"✓ Found {result.get('content_count', 0)} content items")
        else:
            print(f"✓ No content yet (expected): {result.get('message')}")
    else:
        print(f"✗ Failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_generate_content(fingerprint):
    """Test content generation endpoint"""
    
    print(f"\nTesting /rpd/generate-content endpoint...")
    response = requests.post(
        f"{BASE_URL}/rpd/generate-content",
        params={
            "fingerprint": fingerprint,
            "theme_title": "Введение в Python",
            "content_type": "lecture"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Response received")
        print(f"  Message: {result.get('message', 'Content generation placeholder')}")
    else:
        print(f"✗ Failed: {response.status_code}")
        print(f"  Error: {response.text}")


if __name__ == "__main__":
    print("=" * 60)
    print("KPFU LLM Generator - API Test")
    print("=" * 60)
    
    # Test 1: Submit RPD data
    fingerprint = test_submit_rpd_data()
    
    if fingerprint:
        # Test 2: Retrieve content (should be empty initially)
        test_retrieve_content(fingerprint)
        
        # Test 3: Generate content (placeholder for now)
        test_generate_content(fingerprint)
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
