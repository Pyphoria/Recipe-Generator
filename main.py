# main.py
import os
import sys
import requests
from flask import Flask, request, jsonify, Response
from keep_alive import keep_alive

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ACCESS_KEY = os.getenv("ACCESS_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Recipe API running"}), 200

@app.route("/", methods=["POST"])
def generate_recipe():
    # Logging (Render logs)
    print("--- Request received ---", file=sys.stderr)
    print("Headers:", dict(request.headers), file=sys.stderr)
    body_text = request.get_data(as_text=True)
    print("Body:", body_text, file=sys.stderr)

    # optional: x-api-key check
    if ACCESS_KEY:
        client_key = request.headers.get("x-api-key")
        if client_key != ACCESS_KEY:
            return jsonify({"error": "Unauthorized - invalid x-api-key"}), 401

    # parse JSON or fallback to raw text
    data = request.get_json(silent=True)
    if data:
        ingredients = data.get("ingredients") or data.get("prompt") or ""
    else:
        ingredients = body_text.strip()

    ingredients = (ingredients or "").strip()
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    # Call OpenRouter
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Du bist ein hilfreicher Kochassistent."},
            {"role": "user", "content": f"Erstelle ein Rezept mit folgenden Zutaten: {ingredients}"}
        ]
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
    except requests.exceptions.RequestException as e:
        print("RequestException ->", str(e), file=sys.stderr)
        return jsonify({"error": "Request to OpenRouter failed", "details": str(e)}), 502

    print("OpenRouter status:", resp.status_code, file=sys.stderr)
    print("OpenRouter raw response:", resp.text, file=sys.stderr)

    if resp.status_code != 200:
        return jsonify({
            "error": "OpenRouter API request failed",
            "status_code": resp.status_code,
            "details": resp.text
        }), 500

    try:
        result = resp.json()
    except ValueError:
        return jsonify({"error": "OpenRouter returned invalid JSON", "details": resp.text}), 500

    # Extrahiere die Text-Antwort (falls Struktur wie üblich)
    try:
        recipe_text = result["choices"][0]["message"]["content"]
    except Exception:
        return jsonify({"error": "Unexpected response structure from OpenRouter", "response": result}), 500

    # Wenn der Client Text will (Shortcut kann das per Header- oder Query-Flag angeben),
    # sende reinen Text (keine JSON-Escapes)
    accept = request.headers.get("Accept", "")
    raw_flag = request.args.get("raw", "0")
    if "text/plain" in accept.lower() or raw_flag == "1":
        # Rückgabe als plain text → Shortcut zeigt saubere Zeilen an
        return Response(recipe_text, mimetype="text/plain; charset=utf-8")

    # Default: JSON (besteht abwärtskompatibilität)
    return jsonify({"recipe": recipe_text}), 200


if __name__ == "__main__":
    keep_alive(app)
    from threading import Event
    Event().wait()