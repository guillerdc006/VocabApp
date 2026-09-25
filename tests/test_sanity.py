def test_app_creates_clean_database(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_database_starts_empty(client):
    from app.models import Word, SessionHistory

    with client.application.app_context():
        assert Word.query.count() == 0
        assert SessionHistory.query.count() == 0