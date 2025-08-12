from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# API-Key von Render Environment Variables (RENDER Dashboard -> Environment)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

@app.route("/", methods=["POST"])
def generate_recipe():
    try:
        data = request.get_json()
        if not data or "ingredients" not in data:
            return jsonify({"error": "Missing 'ingredients' field"}), 400

        user_input = data["ingredients"]

        # OpenRouter API-Request
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://your-site.com",  # optional, kann deine Render-URL sein
                "X-Title": "Recipe Generator"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "Du bist ein hilfreicher Kochassistent."},
                    {"role": "user", "content": f"Erstelle ein Rezept mit: {user_input}"}
                ]
            },
            timeout=20
        )

        # Falls API nicht 200 zurückgibt, Fehler anzeigen
        if response.status_code != 200:
            return jsonify({
                "error": "OpenRouter API request failed",
                "status_code": response.status_code,
                "details": response.text
            }), 500

        # Antwort verarbeiten
        result_json = response.json()
        recipe_text = result_json["choices"][0]["message"]["content"]

        return jsonify({"recipe": recipe_text})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Request to OpenRouter failed", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
