def test_root_returns_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_returns_alive(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_returns_ready(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["models_loaded"] > 0


def test_list_languages(client):
    response = client.get("/languages")
    assert response.status_code == 200
    pairs = response.json()
    assert len(pairs) > 0
    assert {"source": "en", "target": "es"} in pairs


def test_translate_en_to_es(client):
    response = client.post("/translate", json={
        "text": "Hello, how are you?",
        "source_lang": "en",
        "target_lang": "es",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["translated_text"]
    assert data["source_lang"] == "en"
    assert data["target_lang"] == "es"
    assert data["model_name"]
    assert data["inference_time_ms"] >= 0


def test_translate_es_to_en(client):
    response = client.post("/translate", json={
        "text": "Buenos días amigo",
        "source_lang": "es",
        "target_lang": "en",
    })
    assert response.status_code == 200
    assert response.json()["translated_text"]


def test_translate_unsupported_pair_returns_400(client):
    response = client.post("/translate", json={
        "text": "Hello",
        "source_lang": "en",
        "target_lang": "zz",
    })
    assert response.status_code == 400


def test_translate_empty_text_returns_422(client):
    response = client.post("/translate", json={
        "text": "",
        "source_lang": "en",
        "target_lang": "es",
    })
    assert response.status_code == 422


def test_translate_missing_fields_returns_422(client):
    response = client.post("/translate", json={
        "text": "Hello",
    })
    assert response.status_code == 422


def test_translate_exceeds_max_length_returns_422(client):
    response = client.post("/translate", json={
        "text": "a" * 5001,
        "source_lang": "en",
        "target_lang": "es",
    })
    assert response.status_code == 422