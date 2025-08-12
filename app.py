from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

ACCESS_KEY = os.environ.get("ACCESS_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

@app.route("/get-recipe", methods=["POST"])
def get_recipe():
    client_key = request.headers.get("x-api-key")
    if client_key != ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    ingredients = data.get("ingredients")
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    try:
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Du bist ein kreativer Kochassistent."},
                {"role": "user", "content": f"Erstelle ein Rezept mit folgenden Zutaten: {ingredients}"}
            ]
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=30)

        if response.status_code != 200:
            return jsonify({"error": "OpenRouter API error", "details": response.text}), 500

        ai_result = response.json()
        recipe_text = ai_result["choices"][0]["message"]["content"]

        return jsonify({"recipe": recipe_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)