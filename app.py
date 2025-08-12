from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# API-Key aus Render-Environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@app.route("/", methods=["POST"])
def generate_recipe():
    data = request.get_json()

    # Zutaten aus Shortcut lesen
    ingredients = data.get("ingredients", "")

    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    # Anfrage an OpenRouter senden
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Du bist ein KI-Koch, der Rezepte aus Zutaten erstellt."},
            {"role": "user", "content": f"Erstelle ein Rezept mit folgenden Zutaten: {ingredients}"}
        ]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        return jsonify({"error": "OpenRouter API request failed"}), 500

    result = response.json()
    reply = result["choices"][0]["message"]["content"]

    return jsonify({"recipe": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
