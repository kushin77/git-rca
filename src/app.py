from flask import Flask, request, jsonify, abort
from .store.sql_store import SqlStore
import os


def create_app(db_path=None):
    app = Flask(__name__)
    db_path = db_path or os.environ.get("INVESTIGATIONS_DB", "investigations.db")
    store = SqlStore(db_path)

    @app.route("/api/investigations", methods=["POST"])
    def create_investigation():
        data = request.get_json() or {}
        title = data.get("title", "Untitled Investigation")
        severity = data.get("severity", "medium")
        status = data.get("status", "open")
        inv = store.create_investigation(title=title, severity=severity, status=status, description=data.get("description"))
        return jsonify(inv), 201

    @app.route("/api/investigations/<inv_id>", methods=["GET"])
    def get_investigation(inv_id):
        inv = store.get_investigation(inv_id)
        if not inv:
            abort(404)
        return jsonify(inv)

    @app.route("/api/investigations/<inv_id>", methods=["PATCH"])
    def patch_investigation(inv_id):
        data = request.get_json() or {}
        updated = store.update_investigation(inv_id, data)
        if not updated:
            abort(404)
        return jsonify(updated)

    @app.route("/api/investigations", methods=["GET"])
    def list_investigations():
        status = request.args.get("status")
        severity = request.args.get("severity")
        results = store.list_investigations(status=status, severity=severity)
        return jsonify(results)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
