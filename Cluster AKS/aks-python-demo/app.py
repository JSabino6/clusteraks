import os
import time

import psycopg2
from flask import Flask, jsonify, request


app = Flask(__name__)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "appdb"),
        user=os.getenv("DB_USER", "appuser"),
        password=os.getenv("DB_PASSWORD", "apppass"),
    )


def init_database():
    for attempt in range(30):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS items (
                            id SERIAL PRIMARY KEY,
                            name TEXT NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        )
                        """
                    )
            return
        except psycopg2.OperationalError:
            if attempt == 29:
                raise
            time.sleep(2)


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/")
def index():
    return jsonify(
        app="aks-python-demo",
        message="Aplicacao Python rodando no AKS e usando PostgreSQL StatefulSet",
        endpoints=["GET /items", "POST /items"],
    )


@app.route("/items", methods=["GET", "POST"])
def items():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        name = payload.get("name", "item criado pelo AKS")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO items (name) VALUES (%s) RETURNING id, name, created_at",
                    (name,),
                )
                row = cur.fetchone()

        return jsonify(id=row[0], name=row[1], created_at=row[2].isoformat()), 201

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM items ORDER BY id DESC")
            rows = cur.fetchall()

    return jsonify(
        [
            {"id": row[0], "name": row[1], "created_at": row[2].isoformat()}
            for row in rows
        ]
    )


init_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
