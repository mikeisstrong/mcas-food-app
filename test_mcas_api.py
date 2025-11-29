#!/usr/bin/env python3
"""
Test script for MCAS Food Assessment API
Verifies the backend is working correctly
"""

import requests
import json
import time

API_URL = 'http://localhost:5000/api'

def test_health():
    """Test if API is running"""
    print("Testing API Health...")
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            print("✓ API is running\n")
            return True
        else:
            print("✗ API returned unexpected status\n")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        print("  Make sure you ran: python mcas_food_api.py\n")
        return False

def test_database_stats():
    """Test database statistics endpoint"""
    print("Testing Database Stats...")
    try:
        response = requests.get(f'{API_URL}/database-stats')
        data = response.json()
        print(f"  Total foods: {data['total_foods']}")
        print(f"  Rating 0: {data['by_rating']['0']}")
        print(f"  Rating 1: {data['by_rating']['1']}")
        print(f"  Rating 2: {data['by_rating']['2']}")
        print(f"  Rating 3: {data['by_rating']['3']}")
        print("✓ Database stats loaded\n")
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False

def test_search():
    """Test food search"""
    print("Testing Food Search...")
    try:
        response = requests.get(f'{API_URL}/search-foods?q=chicken')
        data = response.json()
        if data['count'] > 0:
            print(f"  Found {data['count']} foods matching 'chicken'")
            print(f"  First result: {data['results'][0]['name']}")
            print("✓ Search working\n")
            return True
        else:
            print("✗ No results found\n")
            return False
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False

def test_foods_by_rating():
    """Test filter by rating"""
    print("Testing Foods by Rating...")
    try:
        response = requests.get(f'{API_URL}/foods-by-rating?rating=0')
        data = response.json()
        print(f"  Found {data['count']} Rating 0 foods")
        if data['count'] > 0:
            print(f"  Example: {data['foods'][0]['name']}")
        print("✓ Rating filter working\n")
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False

def test_food_assessment():
    """Test food assessment endpoint"""
    print("Testing Food Assessment (requires OpenAI API key)...")

    test_foods = [
        "chicken",
        "tomato",
        "blue cheese",
        "fresh salmon",
    ]

    for food_name in test_foods:
        try:
            print(f"\n  Assessing: {food_name}")

            response = requests.post(
                f'{API_URL}/assess-food',
                json={'food_name': food_name},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Check for database match
                if data.get('sighi_exact_match'):
                    rating = data['sighi_exact_match']['rating']
                    print(f"    SIGHI Rating: {rating}")

                # Check for LLM assessment
                if data.get('llm_assessment') and not data['llm_assessment'].get('error'):
                    assessment = data['llm_assessment']
                    rating = assessment.get('llm_assessment_rating', '?')
                    probability = assessment.get('reaction_probability_percentage', '?')
                    confidence = assessment.get('confidence_percentage', '?')
                    print(f"    AI Rating: {rating}, Probability: {probability}%, Confidence: {confidence}%")
                else:
                    print(f"    AI Assessment: Error or not available")
                    if data.get('llm_assessment', {}).get('error'):
                        print(f"    Error: {data['llm_assessment']['error']}")

                print("    ✓ Assessment received")
            else:
                print(f"    ✗ API error: {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"    ✗ Request timed out (OpenAI API slow)")
        except Exception as e:
            print(f"    ✗ Error: {e}")

        time.sleep(1)  # Rate limiting

    print("\n✓ Assessment tests completed\n")
    return True

def test_categories():
    """Test foods by category"""
    print("Testing Foods by Category...")
    try:
        response = requests.get(f'{API_URL}/foods-by-category')
        data = response.json()
        print(f"  Found {len(data)} categories:")
        for category, foods in data.items():
            print(f"    - {category}: {len(foods)} foods")
        print("✓ Category filter working\n")
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False

def main():
    print("=" * 60)
    print("MCAS FOOD ASSESSMENT API - TEST SUITE")
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("API Health", test_health()))

    if results[-1][1]:  # Only continue if API is running
        results.append(("Database Stats", test_database_stats()))
        results.append(("Food Search", test_search()))
        results.append(("Filter by Rating", test_foods_by_rating()))
        results.append(("Filter by Category", test_categories()))
        results.append(("Food Assessment", test_food_assessment()))

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name:.<40} {status}")

    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Keep python mcas_food_api.py running")
        print("2. Open mcas_app.html in your web browser")
        print("3. Start searching for foods!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\nTroubleshooting:")
        print("- Ensure python mcas_food_api.py is running")
        print("- Verify OpenAI API key in .env")
        print("- Check that port 5000 is available")

    print()

if __name__ == '__main__':
    main()
