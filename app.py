from flask import Flask, request, jsonify
import os
import requests
import sys

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ACCESS_KEY = os.environ.get("ACCESS_KEY")

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "OK", "message": "Recipe API is running"})

@app.route("/get-recipe", methods=["POST"])
def get_recipe():
    try:
        print("\n📩 Request received", file=sys.stderr)
        print("Headers:", dict(request.headers), file=sys.stderr)
        print("Body:", request.data.decode("utf-8"), file=sys.stderr)

        client_key = request.headers.get("x-api-key")
        if not client_key or client_key != ACCESS_KEY:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(force=True)
        if not data or "ingredients" not in data:
            return jsonify({"error": "Missing 'ingredients' field"}), 400

        ingredients = data["ingredients"]
        print(f"✅ Ingredients received: {ingredients}", file=sys.stderr)

        openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "Du bist ein Kochassistent. Erstelle ein einfaches Rezept basierend auf den Zutaten."
                },
                {
                    "role": "user",
                    "content": f"Erstelle ein Rezept mit diesen Zutaten: {ingredients}"
                }
            ]
        }

        openrouter_res = requests.post(openrouter_url, headers=headers, json=payload)
        if openrouter_res.status_code != 200:
            print("❌ OpenRouter API Error:", openrouter_res.text, file=sys.stderr)
            return jsonify({"error": "OpenRouter API request failed"}), 500

        recipe_data = openrouter_res.json()
        recipe_text = recipe_data["choices"][0]["message"]["content"]

        return jsonify({"recipe": recipe_text})

    except Exception as e:
        print(f"⚠️ Server Error: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
