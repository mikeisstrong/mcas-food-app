# MCAS Food Assessment System - Setup Guide

This is an AI-powered Mast Cell Activation Syndrome (MCAS) food assessment tool that combines the SIGHI (Swiss Interest Group Histamine Intolerance) database with OpenAI's GPT-4 for intelligent food compatibility analysis.

## Features

- **SIGHI Database Integration**: 400+ foods with SIGHI compatibility ratings (0-3)
- **AI-Powered Assessment**: Uses OpenAI GPT-4 to assess unknown foods
- **Smart Matching**: Fuzzy matching to find similar foods in database
- **Comprehensive Analysis**: Evaluates histamine content, biogenic amines, liberators, and DAO blockers
- **Reaction Probability**: Estimates likelihood of MCAS reaction with confidence scores
- **Freshness Awareness**: Notes when food compatibility depends on freshness
- **Scientific Explanations**: Provides detailed, evidence-based reasoning

## Project Structure

```
├── mcas_food_api.py              # Flask backend API
├── mcas_app.html                 # Frontend UI
├── sighi_food_database.json      # SIGHI food compatibility database
├── requirements-mcas.txt         # Python dependencies
├── .env                          # Environment variables (API keys)
└── MCAS_SETUP.md                # This file
```

## Prerequisites

- Python 3.8+
- OpenAI API key (GPT-4 access)
- Modern web browser

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements-mcas.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory with your OpenAI API key:

```env
OPENAI_API_KEY=your_api_key_here
```

**Note**: Never commit `.env` to version control. It's already in `.gitignore`.

### 3. Start the Backend API

```bash
python mcas_food_api.py
```

The API will start on `http://localhost:5000`

### 4. Open the Frontend

Open `mcas_app.html` in your web browser:

```bash
# On macOS
open mcas_app.html

# On Linux
xdg-open mcas_app.html

# Or manually open in browser:
# file:///path/to/mcas_app.html
```

## API Endpoints

### Assess a Food
```bash
POST /api/assess-food
Content-Type: application/json

{
  "food_name": "chicken breast"
}
```

**Response**:
```json
{
  "food_name": "chicken breast",
  "sighi_exact_match": {
    "name": "Chicken",
    "rating": 0,
    "category": "Meat",
    "mechanisms": ["H!"],
    "remarks": "Fresh poultry well tolerated, highly perishable"
  },
  "similar_foods": [...],
  "llm_assessment": {
    "llm_assessment_rating": 0,
    "reaction_probability_percentage": 5,
    "confidence_percentage": 95,
    "mechanisms": ["H!"],
    "scientific_explanation": "...",
    "freshness_dependent": true,
    "recommendations": "..."
  }
}
```

### Search Foods
```bash
GET /api/search-foods?q=tomato
```

### Get Foods by Rating
```bash
GET /api/foods-by-rating?rating=2
```

### Get Foods by Category
```bash
GET /api/foods-by-category
```

### Database Statistics
```bash
GET /api/database-stats
```

## Understanding the Assessment

### Compatibility Ratings

- **Rating 0**: Well tolerated, no symptoms expected
- **Rating 1**: Moderately compatible, minor symptoms possible
- **Rating 2**: Incompatible, significant symptoms likely
- **Rating 3**: Very poorly tolerated, severe symptoms expected

### Mechanisms Affecting Histamine

- **H!**: Highly perishable, rapid histamine formation (protein-based foods)
- **H**: High histamine content (aged, fermented, cured foods)
- **A**: Other biogenic amines (tyramine, phenylethylamine)
- **L**: Liberators of mast cell mediators (foods that trigger mast cell activation)
- **B**: Blockers of histamine-degrading enzymes (fermented foods, alcohol)

### Freshness Impact

Many foods have freshness-dependent ratings. Fresh meat/fish is safe (0), but store-refrigerated versions develop high histamine (3). The AI assessment will note when freshness is critical.

## How It Works

1. **User enters food name** in the search box
2. **Backend searches SIGHI database** for exact match
3. **If found**: Returns SIGHI rating and data
4. **If not found or for detailed assessment**:
   - Sends food name to OpenAI GPT-4
   - GPT-4 analyzes using SIGHI database context
   - Returns AI assessment with:
     - Estimated rating (0-3)
     - Reaction probability %
     - Confidence score
     - Mechanisms involved
     - Preparation recommendations
5. **Frontend displays results** with similar foods and comparative data

## SIGHI Database

The database includes **400+ foods** organized into categories:
- Meat & Poultry
- Seafood & Shellfish
- Dairy & Cheese
- Eggs
- Vegetables
- Fruits
- Nuts & Seeds
- Grains
- Herbs & Spices
- Beverages
- Sweeteners
- Additives

Source: Swiss Interest Group Histamine Intolerance (SIGHI)
Updated: April 1, 2023

## Scientific Basis

The assessment framework is based on:

1. **SIGHI Guidelines**: Swiss research on histamine intolerance
2. **Histamine Content**: Measured levels in foods
3. **Biogenic Amines**: Tyramine, phenylethylamine, etc.
4. **Mast Cell Liberators**: Foods that trigger degranulation
5. **DAO Inhibitors**: Fermented foods that block histamine metabolism
6. **Freshness Factor**: Histamine accumulation over time

## Example Queries

- "chicken" → Fresh meat (Rating 0)
- "aged cheddar" → Aged cheese (Rating 2-3)
- "tomato sauce" → Contains histamine liberators (Rating 2)
- "fresh strawberries" → Liberator (Rating 2)
- "rice" → Well tolerated (Rating 0)
- "blue cheese" → Very high histamine (Rating 2)
- "coffee" → Mast cell activating (Rating 1)
- "canned tuna" → Very high histamine (Rating 3)

## Troubleshooting

### API Connection Error
- Make sure Flask server is running: `python mcas_food_api.py`
- Check that port 5000 is not in use
- Verify CORS is enabled in Flask app

### OpenAI API Error
- Verify API key is correct in `.env`
- Check that you have GPT-4 access
- Ensure you have API credits available
- Check OpenAI status page

### No Results
- Try variations of the food name
- Use the database browser to find similar foods
- Check spelling

## Advanced Usage

### Batch Assessment
You can create a CSV of foods to assess:

```python
import json
import requests

foods = ["chicken", "tomato", "blue cheese", "olive oil"]

for food in foods:
    response = requests.post('http://localhost:5000/api/assess-food',
                            json={'food_name': food})
    result = response.json()
    print(f"{food}: Rating {result['llm_assessment']['llm_assessment_rating']}")
```

### Custom Database Filtering
Filter by category or mechanism:

```python
with open('sighi_food_database.json') as f:
    db = json.load(f)

# Get all high-histamine foods
high_histamine = [f for f in db['foods'] if 'H' in f['mechanisms']]

# Get all fruits
fruits = [f for f in db['foods'] if f['category'] == 'Fruits']
```

## Important Disclaimer

This tool is for informational purposes and should not replace professional medical advice. MCAS/Histamine Intolerance is a complex condition, and individual tolerance varies widely. Always:

- Consult with your healthcare provider
- Keep detailed food logs
- Test foods individually
- Note your personal reactions
- Adjust based on your individual tolerance

## Support & Resources

- SIGHI Website: www.mastzellaktivierung.info
- SIGHI German Site: www.histaminintoleranz.ch
- Food List Updates: Check SIGHI website for latest version
- API Documentation: See endpoints above

## License

This tool uses the SIGHI Food Compatibility List. See SIGHI website for license terms.

The Python/JavaScript code is provided as-is for personal use.
