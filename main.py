import requests
from flask import Flask, request, jsonify
from keep_alive import keep_alive

# Dein OpenRouter API-Key
OPENROUTER_API_KEY = "DEIN_API_KEY_HIER"

app = Flask(__name__)

@app.route("/", methods=["POST"])
def generate_recipe():
    data = request.get_json()

    if not data or "zutaten" not in data:
        return jsonify({"error": "Bitte sende ein JSON mit dem Schlüssel 'zutaten'"}), 400

    zutaten = data["zutaten"]

    # Anfrage an OpenRouter
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Du bist ein Kochassistent. Antworte nur mit einem sauberen Rezepttext ohne unnötige JSON-Formatierung."},
                {"role": "user", "content": f"Erstelle ein einfaches Rezept mit diesen Zutaten: {zutaten}"}
            ],
            "max_tokens": 500
        }
    )

    if response.status_code != 200:
        return jsonify({
            "error": "OpenRouter API request failed",
            "status_code": response.status_code,
            "details": response.text
        }), 500

    try:
        result_json = response.json()
        recipe_text = result_json["choices"][0]["message"]["content"]
    except Exception as e:
        return jsonify({"error": "Fehler beim Lesen der API-Antwort", "details": str(e)}), 500

    # Direkt sauberer Text zurück
    return recipe_text

if __name__ == "__main__":
    keep_alive()