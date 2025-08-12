import os
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Bitte die Umgebungsvariable OPENROUTER_API_KEY setzen!")

@app.route("/", methods=["POST"])
def generate_recipe():
    data = request.json
    ingredients = data.get("ingredients", "")

    # Anfrage an OpenRouter
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://deine-domain.de",  # Optional
        "X-Title": "Meine Rezept-App"               # Optional
    }
    payload = {
        "model": "openai/gpt-4o",
        "messages": [
            {"role": "user", "content": f"Schreibe ein Rezept mit diesen Zutaten: {ingredients}"}
        ]
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=15
        )

        # Falls kein Erfolg -> direkt Fehlertext zurückgeben
        if not response.ok:
            return jsonify({
                "error": f"API-Fehler {response.status_code}",
                "details": response.text
            }), 500

        result = response.json()
        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Request fehlgeschlagen", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
