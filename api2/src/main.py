import os

from flask import Flask, jsonify


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({"service": "api2-crypto-index", "status": "ok"})


@app.get("/indexes/ping")
def indexes_ping():
    return jsonify({"message": "api2 crypto index service placeholder"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8002")))
