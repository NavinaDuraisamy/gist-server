# GitHub Gist Server

A simple Flask server that fetches GitHub user gists with caching.

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

## API

```
GET /<username>
GET /<username>?page=1&per_page=10
```

Example:
```bash
curl http://localhost:8080/octocat
```

## Docker

```bash
docker build -t gist-server .
docker run -p 8080:8080 gist-server
```
