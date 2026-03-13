"""Nutrition lookup - USDA API with fallback to common foods database."""
import os
import httpx
from typing import Optional

# Common foods fallback (calories per 100g typical serving, protein per 100g)
COMMON_FOODS = {
    "rice": (130, 2.7),
    "chapati": (297, 11.3),
    "roti": (297, 11.3),
    "dal": (116, 8.8),
    "chicken": (239, 27.0),
    "fish": (206, 22.0),
    "egg": (155, 13.0),
    "curry": (150, 8.0),
    "sabzi": (80, 3.0),
    "vegetables": (35, 2.0),
    "salad": (15, 1.2),
    "paneer": (265, 18.0),
    "milk": (42, 3.4),
    "oats": (389, 16.9),
    "bread": (265, 9.0),
    "idli": (106, 3.5),
    "dosa": (133, 3.7),
    "paratha": (326, 10.4),
    "poha": (250, 5.0),
    "upma": (130, 3.0),
    "soup": (50, 2.0),
    "fruits": (60, 0.8),
    "banana": (89, 1.1),
    "apple": (52, 0.3),
    "yogurt": (59, 10.0),
    "lentils": (116, 9.0),
}


def _get_fallback_nutrition(food_name: str) -> tuple[float, float]:
    """Get approximate nutrition from common foods lookup."""
    food_lower = food_name.lower().strip()
    for key, (cal, pro) in COMMON_FOODS.items():
        if key in food_lower:
            return cal, pro
    return 100.0, 5.0  # Default estimate


async def lookup_nutrition_usda(query: str) -> Optional[tuple[float, float]]:
    """Lookup nutrition via USDA FoodData Central API."""
    api_key = os.environ.get("USDA_API_KEY")
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.nal.usda.gov/fdc/v1/foods/search",
                params={"api_key": api_key, "query": query, "pageSize": 1},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            foods = data.get("foods", [])
            if not foods:
                return None
            food = foods[0]
            nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}
            calories = nutrients.get("Energy", nutrients.get("Calories", 0))
            protein = nutrients.get("Protein", 0)
            return (float(calories), float(protein))
    except Exception:
        return None


async def get_nutrition(food_name: str) -> tuple[float, float]:
    """Get calories and protein for a food. Tries USDA first, then fallback."""
    if not food_name or not food_name.strip():
        return 0.0, 0.0
    result = await lookup_nutrition_usda(food_name)
    if result:
        return result
    return _get_fallback_nutrition(food_name)
