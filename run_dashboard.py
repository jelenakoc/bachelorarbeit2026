import threading
import time
import webbrowser

import uvicorn


HOST = "127.0.0.1"
PORT = 8000
DASHBOARD_URL = f"http://{HOST}:{PORT}/dashboard"


def open_browser_when_ready():
    time.sleep(1.5)
    webbrowser.open(DASHBOARD_URL)


if __name__ == "__main__":
    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
