from flask import Flask, jsonify, request
import requests
import time

app = Flask(__name__)

GITHUB_API_URL = "https://api.github.com"
CACHE = {}
CACHE_TTL = 300  # 5 minutes


def get_cached(key):
    if key in CACHE:
        data, timestamp = CACHE[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
        del CACHE[key]
    return None


def set_cache(key, data):
    CACHE[key] = (data, time.time())


@app.route("/<username>")
def get_user_gists(username):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 30, type=int)

    cache_key = f"{username}:{page}:{per_page}"
    cached = get_cached(cache_key)
    if cached:
        response = jsonify(cached)
        response.headers['X-Cache'] = 'HIT'
        return response

    response = requests.get(
        f"{GITHUB_API_URL}/users/{username}/gists",
        params={"page": page, "per_page": per_page}
    )

    if response.status_code == 404:
        return jsonify({"error": "User not found"}), 404

    if response.status_code != 200:
        return jsonify({"error": "GitHub API error"}), response.status_code

    data = response.json()
    set_cache(cache_key, data)
    return jsonify(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
