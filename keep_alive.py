# keep_alive.py
from threading import Thread
import os

def _run(app):
    # Port von Render (falls PORT gesetzt) oder fallback 8052
    port = int(os.getenv("PORT", os.getenv("PORT", "8052")))
    app.run(host="0.0.0.0", port=port)

def keep_alive(app):
    """
    Startet die übergebene Flask-App in einem Background-Thread.
    Aufruf: keep_alive(app)
    """
    t = Thread(target=lambda: _run(app), daemon=True)
    t.start()