"""SecondShape HTTP interface. Run with `python app.py`."""
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from secondshape.engine import demo_request, solve, validate_plan
from secondshape.proof import verify_export

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(ROOT / "public" / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 100_000


@app.after_request
def secure(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return send_from_directory(ROOT / "public", "index.html")


@app.get("/api/health")
def health():
    return jsonify(service="secondshape", ok=True, engine="python", version="1.0.0", revision=os.environ.get("SECOND_SHAPE_REVISION", os.environ.get("VERCEL_GIT_COMMIT_SHA", "local")))


@app.get("/api/example")
def example():
    return jsonify(demo_request())


@app.post("/api/solve")
def plan():
    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify(error="Send a JSON object containing design and boards."), 400
    try:
        return jsonify(solve(payload))
    except (ValueError, TypeError, KeyError) as error:
        return jsonify(error=str(error)), 400


@app.post("/api/verify")
def verify():
    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify(error="Send an exported plan object."), 400
    try:
        result = verify_export(payload)
        return jsonify(result)
    except (ValueError, TypeError, KeyError) as error:
        return jsonify(error=str(error)), 400


@app.errorhandler(BadRequest)
def bad_json(_):
    return jsonify(error="The request must contain valid JSON."), 400


@app.errorhandler(RequestEntityTooLarge)
def too_large(_):
    return jsonify(error="Keep the plan under 100 KB."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8767")), debug=False)
