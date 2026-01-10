import pytest
from unittest.mock import patch, Mock
from app import app, CACHE


@pytest.fixture
def client():
    app.config["TESTING"] = True
    CACHE.clear()
    with app.test_client() as client:
        yield client


def test_get_user_gists_success(client):
    mock_gists = [{"id": "123", "description": "Test gist"}]

    with patch("app.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_gists)
        response = client.get("/octocat")

    assert response.status_code == 200
    assert response.json == mock_gists


def test_get_user_gists_not_found(client):
    with patch("app.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=404)
        response = client.get("/nonexistent-user-12345")

    assert response.status_code == 404
    assert response.json["error"] == "User not found"


def test_get_user_gists_api_error(client):
    with patch("app.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=500)
        response = client.get("/octocat")

    assert response.status_code == 500
    assert response.json["error"] == "GitHub API error"


def test_pagination(client):
    mock_gists = [{"id": "456"}]

    with patch("app.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_gists)
        response = client.get("/octocat?page=2&per_page=10")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["page"] == 2
        assert call_args[1]["params"]["per_page"] == 10

    assert response.status_code == 200


def test_caching(client):
    mock_gists = [{"id": "789"}]

    with patch("app.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_gists)

        # First request - hits GitHub
        response1 = client.get("/testuser")
        assert response1.status_code == 200
        assert mock_get.call_count == 1

        # Second request - served from cache
        response2 = client.get("/testuser")
        assert response2.status_code == 200
        assert mock_get.call_count == 1  # Still 1, cache hit

        assert response1.json == response2.json


def test_cache_key_includes_pagination(client):
    mock_gists = [{"id": "abc"}]

    with patch("app.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_gists)

        client.get("/user1?page=1&per_page=10")
        client.get("/user1?page=2&per_page=10")  # Different page

        assert mock_get.call_count == 2  # Both hit GitHub


def test_get_octocat_gists_real_api(client):
    """Integration test with real GitHub API."""
    response = client.get("/octocat")

    if response.status_code == 403:
        pytest.skip("GitHub rate limit exceeded")

    assert response.status_code == 200
    gists = response.json
    assert isinstance(gists, list)
    assert len(gists) > 0
    assert "id" in gists[0]
    assert "html_url" in gists[0]
