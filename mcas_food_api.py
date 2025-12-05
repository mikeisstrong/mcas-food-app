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
import concurrent.futures
import threading

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

def generate_assessment_prompt(food_name, database_info, perspective="general"):
    """
    Generate one of three different assessment prompt perspectives
    perspective: "general", "histamine_risk", or "mechanism_analysis"
    """
    base_context = f"""You are an expert in Mast Cell Activation Syndrome (MCAS) and histamine intolerance,
based on the SIGHI (Swiss Interest Group Histamine Intolerance) food compatibility framework.

Here is the SIGHI database information for reference:
{database_info}

Food Assessment Task:
Assess the food: "{food_name}" """

    if perspective == "general":
        specific_prompt = """Provide a comprehensive assessment considering all factors:
- Whether the food exists in SIGHI and its rating
- Histamine content
- Biogenic amine content
- Mechanisms of concern
- Preparation-dependent risks"""

    elif perspective == "histamine_risk":
        specific_prompt = """Focus specifically on HISTAMINE CONTENT AND FRESHNESS:
- What is the baseline histamine level in this food?
- How does freshness affect histamine accumulation?
- What preparation methods minimize histamine?
- Age, fermentation, and storage time impacts"""

    elif perspective == "mechanism_analysis":
        specific_prompt = """Focus on specific MECHANISMS affecting MCAS:
- Which mechanisms apply? (H = histamine, A = amines, L = liberators, B = DAO blockers)
- How severely does each mechanism affect MCAS patients?
- What are cross-reaction risks?
- What is the biological basis for concern?"""

    prompt = base_context + "\n" + specific_prompt + """

Provide your assessment in this JSON format:
{
  "food_name": "%s",
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
  "recommendations": "practical advice for MCAS sufferers",
  "perspective_focus": "%s"
}

Be conservative in your assessment. When in doubt, rate higher (worse), not lower.""" % (food_name, perspective)

    return prompt

def assess_food_single_prompt(food_name, database_info, perspective="general"):
    """Execute a single assessment prompt and return parsed JSON"""
    prompt = generate_assessment_prompt(food_name, database_info, perspective)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.choices[0].message.content

        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            return {"error": "No JSON found in response", "raw_response": response_text}

    except Exception as e:
        return {"error": f"OpenAI API error: {str(e)}", "food_name": food_name}

def synthesize_assessments(food_name, database_info, assessments, sighi_rating=None, retry_count=0, is_exact_match=None):
    """
    Use a 4th AI call to synthesize 3 assessments into one master response
    Ensures SIGHI alignment by re-running if needed

    is_exact_match: Boolean indicating if sighi_rating is from exact match or similar food
    """
    assessments_str = json.dumps(assessments, indent=2)

    # Adjust prompt based on retry count and match type
    if retry_count == 0:
        if is_exact_match:
            alignment_instruction = "CRITICAL: If this food exists in SIGHI, the final_rating MUST match sighi_rating."
        elif sighi_rating is not None:
            alignment_instruction = f"IMPORTANT: A similar SIGHI food has rating {sighi_rating}. Use this as guidance, and your final_rating should be the same or higher (more cautious)."
        else:
            alignment_instruction = "Provide your best assessment based on the 3 expert perspectives."
    else:
        alignment_instruction = f"CRITICAL REQUIREMENT: This food exists in SIGHI with rating {sighi_rating}. Your final_rating MUST be exactly {sighi_rating}. No exceptions. If you previously assigned a different rating, you were incorrect."

    synthesis_prompt = f"""You are an expert synthesizer of MCAS food assessments. You have received 3 independent
expert assessments of the food: "{food_name}"

SIGHI Database Context:
{database_info}

Here are the 3 independent assessments to synthesize:

{assessments_str}

Your task:
1. Evaluate all 3 assessments for consistency and quality
2. Identify areas of agreement and disagreement
3. Create ONE master assessment that:
   - Represents the consensus view
   - Is conservative (errs on the side of caution for MCAS)
   - Provides the most complete and accurate assessment
   - MUST ALIGN with SIGHI database ratings if the food exists there

Return ONLY a single JSON object in this format:
{{
  "food_name": "{food_name}",
  "found_in_sighi": true/false,
  "sighi_rating": 0-3 or null,
  "final_rating": 0-3,
  "confidence_percentage": 70-95,
  "reaction_probability": "low/moderate/high/very-high",
  "reaction_probability_percentage": 0-100,
  "mechanisms": ["H", "A", "L", "B"] (which apply),
  "key_concerns": ["concern1", "concern2"],
  "preparation_notes": "tips for preparing this food safely",
  "freshness_dependent": true/false,
  "scientific_explanation": "2-3 sentences explaining the assessment",
  "recommendations": "practical advice for MCAS sufferers",
  "synthesis_notes": "explanation of how the 3 assessments were synthesized",
  "sighi_alignment_verified": true/false
}}

{alignment_instruction}
Never allow AI assessment to override SIGHI database ratings."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1200,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )

        response_text = response.choices[0].message.content

        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            return {"error": "No JSON found in synthesis response", "raw_response": response_text}

    except Exception as e:
        return {"error": f"Synthesis error: {str(e)}", "food_name": food_name}

def assess_food_with_llm(food_name, database_info, existing_food_data=None, is_exact_match=None):
    """
    Use 3 simultaneous AI assessments + 1 synthesizer
    Ensures high quality, consistent, SIGHI-aligned assessments
    Re-runs synthesis if AI disagrees with SIGHI

    is_exact_match: Boolean indicating if existing_food_data is exact match or similar
    """

    # Determine if this is an exact match or similar food
    if is_exact_match is None and existing_food_data:
        is_exact_match = (existing_food_data.get('name', '').lower() == food_name.lower())

    # Execute 3 assessments in parallel
    perspectives = ["general", "histamine_risk", "mechanism_analysis"]
    assessments = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(assess_food_single_prompt, food_name, database_info, p): p
            for p in perspectives
        }

        for future in concurrent.futures.as_completed(futures):
            assessment = future.result()
            assessments.append(assessment)

    # Synthesize the 3 assessments into 1 master response
    # Retry if disagreement with SIGHI
    max_retries = 2
    retry_count = 0
    synthesized = None

    while retry_count <= max_retries:
        synthesized = synthesize_assessments(
            food_name,
            database_info,
            assessments,
            sighi_rating=existing_food_data.get('rating') if existing_food_data else None,
            retry_count=retry_count,
            is_exact_match=is_exact_match
        )

        # Check for errors in synthesis
        if "error" in synthesized:
            logger.warning(f"Synthesis error for {food_name}: {synthesized.get('error')}")
            break

        # SIGHI validation: check alignment
        if existing_food_data:
            sighi_rating = existing_food_data.get('rating')
            ai_rating = synthesized.get('final_rating')

            synthesized['found_in_sighi'] = is_exact_match if is_exact_match is not None else True
            synthesized['sighi_reference'] = existing_food_data.get('name', food_name)
            synthesized['sighi_rating'] = sighi_rating

            if ai_rating == sighi_rating:
                # Alignment verified!
                synthesized['sighi_alignment_verified'] = True
                if is_exact_match:
                    synthesized['alignment_note'] = "AI assessment aligns with SIGHI database (exact match)"
                else:
                    synthesized['alignment_note'] = f"AI assessment aligns with similar SIGHI food: {existing_food_data.get('name')}"
                logger.info(f"SIGHI alignment verified for {food_name}: rating {ai_rating}")
                break
            else:
                # Disagreement detected
                if retry_count < max_retries:
                    logger.warning(
                        f"SIGHI alignment failed for {food_name}: "
                        f"AI rated {ai_rating} but SIGHI rated {sighi_rating}. "
                        f"Retrying synthesis (attempt {retry_count + 1}/{max_retries})"
                    )
                    retry_count += 1
                else:
                    # Max retries reached, use SIGHI rating
                    logger.warning(
                        f"Max retries reached for {food_name}. "
                        f"Using SIGHI rating {sighi_rating} instead of AI rating {ai_rating}"
                    )
                    synthesized['sighi_alignment_verified'] = False
                    ref_food = existing_food_data.get('name', 'database')
                    synthesized['alignment_note'] = (
                        f"AI initially rated {ai_rating} but SIGHI database rates {ref_food} as {sighi_rating}. "
                        "Using SIGHI rating as ground truth."
                    )
                    synthesized['final_rating'] = sighi_rating
                    break
        else:
            # No SIGHI data, assessment is complete
            break

    return {
        "individual_assessments": assessments,
        "synthesized_assessment": synthesized
    }

@app.route('/api/assess-food', methods=['POST', 'OPTIONS'])
def assess_food():
    """Main API endpoint for food assessment"""
    logger.info(f"Request received: {request.method} {request.path}")

    if request.method == 'OPTIONS':
        return '', 204

    data = request.json
    food_name = data.get('food_name', '').strip()

    if not food_name:
        logger.error("food_name is required")
        return jsonify({"error": "food_name is required"}), 400

    logger.info(f"Assessing food: {food_name} - Starting 3-prompt synthesis process")

    # Check if food exists in SIGHI database
    exact_match = get_food_by_name(food_name)
    similar_foods = find_similar_foods(food_name, limit=3)

    # Build response
    response = {
        "food_name": food_name,
        "sighi_exact_match": exact_match,
        "similar_foods": similar_foods
    }

    # Get LLM assessment with 3-prompt synthesis + SIGHI validation
    # Use exact match if available, otherwise use first similar food for guidance
    sighi_reference = exact_match or (similar_foods[0] if similar_foods else None)
    database_info = build_food_context()
    llm_assessment = assess_food_with_llm(food_name, database_info, sighi_reference)
    response["assessment"] = llm_assessment

    # Include database rating if exact match exists
    if exact_match:
        response["database_rating"] = {
            "rating": exact_match['rating'],
            "category": exact_match['category'],
            "mechanisms": exact_match['mechanisms'],
            "remarks": exact_match['remarks']
        }

    logger.info(f"Assessment complete for {food_name}")
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
