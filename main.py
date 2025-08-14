# main.py
import os
import sys
import requests
import json
import re
from flask import Flask, request, jsonify
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
    # Logging (für Render-Console)
    print("\n--- Request received ---", file=sys.stderr)
    print("Headers:", dict(request.headers), file=sys.stderr)
    body_text = request.get_data(as_text=True)
    print("Body:", body_text, file=sys.stderr)

    # Optional: Header-Authorization via ACCESS_KEY
    if ACCESS_KEY:
        client_key = request.headers.get("x-api-key")
        if client_key != ACCESS_KEY:
            return jsonify({"error": "Unauthorized - invalid x-api-key"}), 401

    # Robustes Parsen des Eingangs
    data = request.get_json(silent=True)
    if data:
        ingredients = data.get("ingredients") or data.get("prompt") or ""
        ingredients = ingredients.strip()
        if not ingredients:
            return jsonify({"error": "No ingredients provided in JSON"}), 400
    else:
        # Fallback: rohe Body-Text als Zutaten verwenden
        fallback = (body_text or "").strip()
        if not fallback:
            return jsonify({"error": "No JSON body and no raw text provided"}), 400
        ingredients = fallback

    # Compose OpenRouter Request
    payload = {
        "model": OPENROUTER_MODEL,
        "max_tokens": int(os.getenv("MAX_TOKENS", "800")),  # sicherer Default
        "messages": [
            {"role": "system", "content": "Du bist ein hilfreicher Kochassistent."},
            {"role": "user", "content": f"Erstelle ein klares, gut strukturiertes Rezept mit folgenden Zutaten: {ingredients}"}
        ]
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=25)
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

    # Parse safe
    try:
        result = resp.json()
    except ValueError:
        return jsonify({"error": "OpenRouter returned invalid JSON", "details": resp.text}), 500

    # Extrahiere rohen Text (fallback falls Struktur anders)
    try:
        recipe_text = result["choices"][0]["message"]["content"]
    except Exception:
        # gib komplette Antwort zurück, damit debugbar
        return jsonify({"error": "Unexpected response structure from OpenRouter", "response": result}), 500

    # ------------------------------------------------------------------
    # Jetzt: recipe_text säubern -> recipe_clean (Plain Text, ohne Markdown)
    # ------------------------------------------------------------------

    # 1) Falls API evtl. escaped newlines liefert (e.g. "\\n"), ent-escapen
    try:
        # Achtung: nur wenn escapes vorhanden sind
        if "\\n" in recipe_text or "\\t" in recipe_text:
            recipe_text = recipe_text.encode('utf-8').decode('unicode_escape')
    except Exception:
        # falls ent-escapen schiefgeht, weiter mit Original
        pass

    clean = recipe_text

    # 2) Entferne Markdown-Header (###, ##, #)
    clean = re.sub(r'(?m)^\s{0,3}#{1,6}\s*', '', clean)

    # 3) Entferne fett/italic-Markup **text** or __text__ or *text* or _text_
    clean = re.sub(r'(\*\*|__)(.*?)\1', r'\2', clean)
    clean = re.sub(r'(\*|_)(.*?)\1', r'\2', clean)

    # 4) Entferne Inline-Code `code`
    clean = re.sub(r'`([^`]*)`', r'\1', clean)

    # 5) Entferne Codeblocks ``` ``` (inkl. Inhalt optional, hier wir behalten Inhalt)
    clean = re.sub(r'```(?:[\s\S]*?)```', lambda m: m.group(0).strip('`'), clean)

    # 6) Ersetze horizontale Linien (--- oder *** ) durch eine Leerzeile
    clean = re.sub(r'(?m)^[\-\*\_]{3,}\s*$', '\n', clean)

    # 7) Listenformate: - item  oder * item  -> behalte als "- item"
    clean = re.sub(r'(?m)^\s*[-\*\+]\s+', '- ', clean)

    # 8) Entferne doppelte Leerzeichen am Zeilenanfang und Trim je Zeile
    clean = '\n'.join(line.strip() for line in clean.splitlines())

    # 9) Reduziere übermäßige Leerzeilen (max 2)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

    # 10) Optional: entferne führende/trailing Sonderzeichen in Zeilen
    clean = '\n'.join(line.strip(" \t") for line in clean.splitlines()).strip()

    # Ergebnis zurückgeben: roh + sauber
    return jsonify({
        "recipe": recipe_text,
        "recipe_clean": clean
    }), 200


if __name__ == "__main__":
    # keep_alive startet die Flask-App im Hintergrundthread und blockiert nicht
    keep_alive(app)
    # Verhindere, dass der Prozess beendet wird
    from threading import Event
    Event().wait()