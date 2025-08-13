from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

@app.route("/", methods=["POST"])
def handle_request():
    data = request.get_json()
    if not data or "ingredients" not in data:
        return jsonify({"error": "No ingredients provided"}), 400

    user_ingredients = data["ingredients"]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "Du bist ein hilfreicher Kochassistent."},
                    {"role": "user", "content": f"Erstelle ein kreatives Rezept mit folgenden Zutaten: {user_ingredients}"}
                ]
            },
            timeout=20
        )

        if response.status_code != 200:
            return jsonify({
                "error": "OpenRouter API request failed",
                "status_code": response.status_code,
                "details": response.text
            }), response.status_code

        result_json = response.json()
        answer = result_json["choices"][0]["message"]["content"]

        return jsonify({"recipe": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "Backend läuft!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)