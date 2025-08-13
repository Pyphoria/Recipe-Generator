# main.py
import os
import requests
import json
import threading
from flask import Flask, request, jsonify
from keep_alive import keep_alive   # keep_alive erwartet das Flask-App-Objekt

app = Flask(__name__)

# --- Konfiguration über Environment Variables (Render) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Pflicht: setze in Render
ACCESS_KEY = os.getenv("ACCESS_KEY")                  # Dein Shortcut-Header key (x-api-key)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")  # optional

# --- Healthcheck (für UptimeRobot) ---
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Recipe API running"})

# --- Haupt-Endpoint für Shortcut ---
@app.route("/recipe", methods=["POST"])
def recipe():
    # Überprüfe/Logge Header (für Debugging kannst du hier prints einbauen)
    incoming_key = request.headers.get("x-api-key")
    if not ACCESS_KEY:
        # Falls ACCESS_KEY nicht gesetzt wurde, verweigern wir nicht, sondern warnen — optional kannst du das strenger machen
        pass
    else:
        if incoming_key != ACCESS_KEY:
            return jsonify({"error": "Unauthorized - invalid x-api-key"}), 401

    # JSON lesen (robust)
    data = request.get_json(silent=True) or {}
    # Akzeptiere entweder "ingredients" oder "prompt"
    ingredients = data.get("ingredients") or data.get("prompt") or ""
    ingredients = ingredients.strip()
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    # Anfrage an OpenRouter bauen
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Du bist ein hilfreicher Kochassistent."},
            {"role": "user", "content": f"Erstelle ein Rezept mit folgenden Zutaten: {ingredients}"}
        ]
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Request to OpenRouter failed", "details": str(e)}), 500

    # Wenn kein 200, gib die Response zurück (inkl. status und body)
    if resp.status_code != 200:
        return jsonify({
            "error": "OpenRouter API request failed",
            "status_code": resp.status_code,
            "details": resp.text
        }), max(500, resp.status_code)

    # Parse JSON sicher
    try:
        result = resp.json()
    except ValueError:
        return jsonify({
            "error": "OpenRouter returned invalid JSON",
            "details": resp.text
        }), 500

    # Extrahiere Inhalt (sicherer Zugriff)
    try:
        recipe_text = result["choices"][0]["message"]["content"]
    except Exception:
        # Falls Struktur anders ist, gib das ganze JSON als Debug zurück
        return jsonify({
            "error": "Unexpected response structure from OpenRouter",
            "response": result
        }), 500

    return jsonify({"recipe": recipe_text})


# --- Wenn main.py direkt ausgeführt wird: keep_alive starten und main-Thread blockieren ---
if __name__ == "__main__":
    # Start die Flask-App in einem Hintergrundthread (keep_alive macht app.run)
    keep_alive(app)
    # Blockiere den Hauptthread, damit Render-Prozess nicht endet
    threading.Event().wait()
