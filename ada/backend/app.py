import os
import argparse

from flask import Flask, jsonify, request

from routes.api_routes import register_api_routes
from routes.tagger_routes import register_tagger_routes
from routes.web_routes import register_web_routes
from tagger.security import MAX_JSON_BODY_BYTES, check_access, validate_content_length

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = MAX_JSON_BODY_BYTES

TAXONOMY_BASE_DIR = os.path.join(os.path.dirname(__file__), "taxonomies")


@app.errorhandler(404)
def handle_404(err):
    """
    Ensure API clients always receive JSON, not HTML error pages.
    """
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found", "path": request.path}), 404
    return err


@app.errorhandler(405)
def handle_405(err):
    """
    Ensure API clients always receive JSON, not HTML error pages.
    """
    if request.path.startswith("/api/"):
        return (
            jsonify(
                {
                    "error": "Method not allowed",
                    "path": request.path,
                    "method": request.method,
                }
            ),
            405,
        )
    return err


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    """
    Prevent Flask's default HTML 500 page for API routes.
    """
    if request.path.startswith("/api/"):
        app.logger.error("Unhandled API error on %s (%s)", request.path, err.__class__.__name__)
        return jsonify({"error": "Internal server error"}), 500
    raise err


@app.errorhandler(503)
def handle_503(err):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Service temporarily unavailable"}), 503
    return err


@app.before_request
def protect_tagger_api():
    if not request.path.startswith("/api/tagger"):
        return None
    if not validate_content_length(request, MAX_JSON_BODY_BYTES):
        return jsonify({"error": "Request body exceeds the configured size limit."}), 413
    allowed, message = check_access(request)
    if not allowed:
        return jsonify({"error": message}), 401
    return None


register_web_routes(app)
register_api_routes(app, TAXONOMY_BASE_DIR)
register_tagger_routes(app)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000, help="Port to run the Flask app on")
    args = parser.parse_args()

    app.run(debug=True, port=args.port)
