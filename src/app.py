from flask import Flask, request, jsonify, abort, render_template
from .store.sql_store import SqlStore
import os
import pathlib


def create_app(db_path=None):
    # Ensure Flask locates templates/static at repo-level
    base_dir = pathlib.Path(__file__).resolve().parent.parent
    template_dir = str(base_dir / "templates")
    static_dir = str(base_dir / "static")
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    db_path = db_path or os.environ.get("INVESTIGATIONS_DB", str(base_dir / "investigations.db"))
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

    @app.route("/investigations/<inv_id>")
    def investigation_canvas(inv_id):
        inv = store.get_investigation(inv_id)
        if not inv:
            # Render a demo canvas for test/demo purposes
            inv = {
                "id": inv_id,
                "title": "Demo Investigation",
                "status": "open",
                "severity": "medium",
                "description": "This is a demo investigation for the canvas prototype.",
            }
        return render_template("investigation.html", investigation=inv)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
