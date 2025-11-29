"""
MCAS Food Assessment API with LLM Integration
Uses OpenAI GPT-4-Nano to assess foods based on SIGHI database and scientific principles
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import difflib
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mcas_api.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Load SIGHI database
with open('sighi_food_database.json', 'r') as f:
    sighi_db = json.load(f)

def find_similar_foods(query, limit=5):
    """Find similar foods in database using fuzzy matching"""
    food_names = [food['name'].lower() for food in sighi_db['foods']]
    matches = difflib.get_close_matches(query.lower(), food_names, n=limit, cutoff=0.6)

    results = []
    for match in matches:
        food = next(f for f in sighi_db['foods'] if f['name'].lower() == match)
        results.append(food)
    return results

def get_food_by_name(name):
    """Get exact food match from database"""
    for food in sighi_db['foods']:
        if food['name'].lower() == name.lower():
            return food
    return None

def build_food_context():
    """Build context string from SIGHI database for LLM"""
    context = "SIGHI Food Compatibility Database Summary:\n\n"

    # Group foods by rating
    by_rating = {0: [], 1: [], 2: [], 3: []}
    for food in sighi_db['foods']:
        by_rating[food['rating']].append(food['name'])

    context += "Rating 0 (Well Tolerated):\n"
    context += ", ".join(by_rating[0][:20]) + "...\n\n"

    context += "Rating 1 (Moderate - Caution):\n"
    context += ", ".join(by_rating[1][:15]) + "...\n\n"

    context += "Rating 2 (Incompatible):\n"
    context += ", ".join(by_rating[2][:15]) + "...\n\n"

    context += "Rating 3 (Very Poor):\n"
    context += ", ".join(by_rating[3][:10]) + "...\n\n"

    context += f"Total foods in database: {len(sighi_db['foods'])}\n"
    context += "Mechanisms affecting histamine metabolism:\n"
    context += "- H! = Highly perishable, rapid histamine formation\n"
    context += "- H = High histamine content\n"
    context += "- A = Other biogenic amines\n"
    context += "- L = Liberators of mast cell mediators\n"
    context += "- B = Blockers of histamine-degrading enzymes (DAO)\n"

    return context

def assess_food_with_llm(food_name, database_info, existing_food_data=None):
    """
    Use OpenAI to assess a food for MCAS compatibility
    References SIGHI database and scientific principles
    """

    # Build the prompt
    prompt = f"""You are an expert in Mast Cell Activation Syndrome (MCAS) and histamine intolerance,
based on the SIGHI (Swiss Interest Group Histamine Intolerance) food compatibility framework.

Here is the SIGHI database information for reference:
{database_info}

Food Assessment Task:
Assess the food: "{food_name}"

If this food exists in the SIGHI database, use that rating as the primary source.
If it doesn't exist or is a brand/prepared food, assess based on these principles:

1. HISTAMINE CONTENT:
   - Fresh, perishable proteins: Very high risk (especially aged/cured/fermented)
   - Fresh produce: Generally low histamine
   - Fermented foods: High histamine
   - Cured/smoked meats: Very high histamine

2. BIOGENIC AMINES (A):
   - Citrus fruits, bananas, nuts: contain tyramine, phenylethylamine
   - Chocolate: contains phenylethylamine
   - Aged foods: accumulate amines

3. HISTAMINE LIBERATORS (L):
   - Tomatoes, strawberries, raspberries, spinach
   - Seafood (especially shellfish)
   - Chocolate, cocoa
   - Citrus fruits
   - Nuts (especially walnuts, cashews)
   - Spices (cumin, mustard, curry)

4. DAO BLOCKERS/INHIBITORS (B):
   - Alcohol
   - Black tea, green tea
   - Fermented foods
   - Iodine supplements

5. FRESHNESS DEPENDENCY:
   - Fresh = much lower histamine
   - Stored = higher histamine accumulation
   - Aged/Fermented = very high histamine

Provide your assessment in this JSON format:
{{
  "food_name": "{food_name}",
  "found_in_sighi": true/false,
  "sighi_rating": 0-3 or null,
  "llm_assessment_rating": 0-3,
  "confidence_percentage": 70-95,
  "reaction_probability": "low/moderate/high/very-high",
  "reaction_probability_percentage": 0-100,
  "mechanisms": ["H", "A", "L", "B"] (which apply),
  "key_concerns": ["concern1", "concern2"],
  "preparation_notes": "tips for preparing this food safely",
  "freshness_dependent": true/false,
  "scientific_explanation": "2-3 sentences explaining the assessment",
  "recommendations": "practical advice for MCAS sufferers"
}}

Be conservative in your assessment. When in doubt, rate higher (worse), not lower."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response
        response_text = response.choices[0].message.content

        # Extract JSON from response
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            assessment = json.loads(json_str)
        except:
            assessment = {"error": "Could not parse LLM response", "raw_response": response_text}

        return assessment

    except Exception as e:
        return {
            "error": f"OpenAI API error: {str(e)}",
            "food_name": food_name
        }

@app.route('/api/assess-food', methods=['POST', 'OPTIONS'])
def assess_food():
    """Main API endpoint for food assessment"""
    logger.info(f"Request received: {request.method} {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")

    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for CORS preflight")
        return '', 204

    data = request.json
    logger.info(f"Request data: {data}")
    food_name = data.get('food_name', '').strip()

    if not food_name:
        logger.error("food_name is required")
        return jsonify({"error": "food_name is required"}), 400

    logger.info(f"Assessing food: {food_name}")

    # Check if food exists in SIGHI database
    exact_match = get_food_by_name(food_name)
    similar_foods = find_similar_foods(food_name, limit=3)

    # Build response
    response = {
        "food_name": food_name,
        "sighi_exact_match": exact_match,
        "similar_foods": similar_foods
    }

    # Get LLM assessment
    database_info = build_food_context()
    llm_assessment = assess_food_with_llm(food_name, database_info, exact_match)
    response["llm_assessment"] = llm_assessment

    # Combine with database data if exact match exists
    if exact_match:
        response["database_rating"] = {
            "rating": exact_match['rating'],
            "category": exact_match['category'],
            "mechanisms": exact_match['mechanisms'],
            "remarks": exact_match['remarks']
        }

    logger.info(f"Assessment complete for {food_name}, returning response")
    return jsonify(response)

@app.route('/api/search-foods', methods=['GET'])
def search_foods():
    """Search SIGHI database for foods"""
    query = request.args.get('q', '').lower()

    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    # Search by name
    results = []
    for food in sighi_db['foods']:
        if query in food['name'].lower():
            results.append(food)
            if len(results) >= 10:
                break

    return jsonify({
        "query": query,
        "results": results,
        "count": len(results)
    })

@app.route('/api/foods-by-rating', methods=['GET'])
def foods_by_rating():
    """Get all foods grouped by SIGHI rating"""
    rating = request.args.get('rating')

    if rating is not None:
        try:
            rating = int(rating)
            foods = [f for f in sighi_db['foods'] if f['rating'] == rating]
            return jsonify({
                "rating": rating,
                "foods": foods,
                "count": len(foods)
            })
        except:
            return jsonify({"error": "Invalid rating. Must be 0, 1, 2, or 3"}), 400

    # Return all grouped by rating
    by_rating = {0: [], 1: [], 2: [], 3: []}
    for food in sighi_db['foods']:
        by_rating[food['rating']].append(food)

    return jsonify(by_rating)

@app.route('/api/foods-by-category', methods=['GET'])
def foods_by_category():
    """Get foods grouped by category"""
    categories = {}
    for food in sighi_db['foods']:
        cat = food['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(food)

    return jsonify(categories)

@app.route('/api/database-stats', methods=['GET'])
def database_stats():
    """Get statistics about the SIGHI database"""
    total = len(sighi_db['foods'])
    by_rating = {0: 0, 1: 0, 2: 0, 3: 0}
    categories = {}

    for food in sighi_db['foods']:
        by_rating[food['rating']] += 1
        cat = food['category']
        categories[cat] = categories.get(cat, 0) + 1

    return jsonify({
        "total_foods": total,
        "by_rating": {str(k): v for k, v in by_rating.items()},
        "categories": categories,
        "database_updated": sighi_db['metadata']['updated']
    })

@app.route('/', methods=['GET'])
def index():
    """Serve the main HTML application"""
    try:
        with open('mcas_app.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({"error": "Application not found"}), 404

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "MCAS Food Assessment API"})

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("MCAS Food Assessment API Starting")
    logger.info(f"Loading SIGHI database: {len(sighi_db['foods'])} foods loaded")
    logger.info(f"OpenAI API Key configured: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    logger.info("=" * 60)

    # Get port from environment variable (Railway uses PORT) or default to 5001
    port = int(os.getenv('PORT', 5001))

    logger.info(f"API listening on 0.0.0.0:{port}")
    logger.info("Access from:")
    logger.info("  - Local: http://127.0.0.1:{port}")
    logger.info("  - Network: http://192.168.2.202:{port}")
    logger.info("Endpoints available:")
    logger.info("  GET / - Main application")
    logger.info("  POST /api/assess-food - Assess a food")
    logger.info("  GET /api/search-foods - Search foods")
    logger.info("  GET /api/foods-by-rating - Filter by rating")
    logger.info("  GET /api/foods-by-category - Filter by category")
    logger.info("  GET /api/database-stats - Get database stats")
    logger.info("  GET /health - Health check")
    logger.info("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
