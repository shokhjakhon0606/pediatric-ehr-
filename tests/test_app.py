def test_app_creation(app):
    assert app is not None
    assert app.config["SECRET_KEY"] == "test-secret-key"


def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.location


def test_login_page(client):
    response = client.get("/login")

    assert response.status_code == 200