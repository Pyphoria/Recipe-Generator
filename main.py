# main.py
import os
import sys
import requests
import json
from flask import Flask, request, jsonify
from keep_alive import keep_alive

app = Flask(__name__)

# --- Config (aus Render Environment) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Pflicht: setze in Render
ACCESS_KEY = os.getenv("ACCESS_KEY")                  # optional: Header x-api-key Kontrolle
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Healthcheck (für UptimeRobot) ---
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Recipe API running"}), 200

# --- Haupt-Endpoint: akzeptiert POST mit JSON {"ingredients": "..."} oder {"prompt": "..."} ---
@app.route("/", methods=["POST"])
def generate_recipe():
    # Debug-Logging in Render-Logs (rot sichtbar)
    print("\n--- Request received ---", file=sys.stderr)
    print("Headers:", dict(request.headers), file=sys.stderr)
    try:
        body_bytes = request.get_data()
        body_text = body_bytes.decode("utf-8") if body_bytes else ""
    except Exception:
        body_text = "<could not decode body>"
    print("Body:", body_text, file=sys.stderr)

    # optional: x-api-key autorisierung, nur wenn ACCESS_KEY gesetzt ist
    if ACCESS_KEY:
        client_key = request.headers.get("x-api-key")
        if client_key != ACCESS_KEY:
            return jsonify({"error": "Unauthorized - invalid x-api-key"}), 401

    # robust JSON-parsing (akzeptiert JSON oder plain text)
    data = request.get_json(silent=True)
    if not data:
        # Versuch: falls Shortcut nicht als JSON gesendet hat, nehmen wir den raw body als ingredients
        try:
            # body_text könnte z. B. 'Tomaten, Käse' sein
            fallback = body_text.strip()
            if fallback:
                ingredients = fallback
            else:
                return jsonify({"error": "No JSON body and no raw text provided"}), 400
        except Exception:
            return jsonify({"error": "Unable to parse request body"}), 400
    else:
        # Akzeptiere sowohl "ingredients" als auch "prompt"
        ingredients = data.get("ingredients") or data.get("prompt") or ""
        ingredients = ingredients.strip()
        if not ingredients:
            return jsonify({"error": "No ingredients provided in JSON"}), 400

    # Compose OpenRouter payload
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

    # Debug: Status & raw text
    print("OpenRouter status:", resp.status_code, file=sys.stderr)
    print("OpenRouter raw response:", resp.text, file=sys.stderr)

    if resp.status_code != 200:
        # gib Status und body zurück, damit du im Shortcut genau siehst was schief läuft
        return jsonify({
            "error": "OpenRouter API request failed",
            "status_code": resp.status_code,
            "details": resp.text
        }), 500

    # parse JSON sicher
    try:
        result = resp.json()
    except ValueError:
        return jsonify({
            "error": "OpenRouter returned invalid JSON",
            "details": resp.text
        }), 500

    # sichere Extraktion der Antwort
    try:
        recipe_text = result["choices"][0]["message"]["content"]
    except Exception:
        # fallback: gib die ganze Antwort zurück, damit man debuggen kann
        return jsonify({
            "error": "Unexpected response structure from OpenRouter",
            "response": result
        }), 500

    return jsonify({"recipe": recipe_text}), 200


# --- Starten (keep_alive startet die Flask-App in Hintergrundthread) ---
if __name__ == "__main__":
    # keep_alive startet app.run(host=..., port=...)
    keep_alive(app)
    # blockieren, damit Prozess nicht endet
    from threading import Event
    Event().wait()