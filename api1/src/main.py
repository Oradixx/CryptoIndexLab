import os

from flask import Flask, jsonify


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({"service": "api1-users-auth", "status": "ok"})


@app.get("/auth/ping")
def auth_ping():
    return jsonify({"message": "api1 users/auth service placeholder"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
