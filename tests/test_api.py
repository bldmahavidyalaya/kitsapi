import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import engine
from sqlmodel import SQLModel


@pytest.fixture()
def client():
    # ensure tables exist for tests
    SQLModel.metadata.create_all(engine)
    return TestClient(app)


def test_health(client):
    r = client.get('/api/v1/health')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok'}


def test_items_crud(client):
    # create
    payload = {'name': 'Test', 'price': 9.99, 'description': 'abc'}
    r = client.post('/api/v1/items', json=payload)
    assert r.status_code == 200
    item = r.json()
    assert item['name'] == 'Test'

    # list
    r = client.get('/api/v1/items')
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1


def test_formats_list(client):
    """Test listing available formats."""
    r = client.get('/api/v1/convert/formats')
    assert r.status_code == 200
    data = r.json()
    assert 'categories' in data
    assert 'document' in data['categories']
    assert 'image' in data['categories']


def test_file_hash(client):
    """Test file hash generation."""
    from io import BytesIO
    test_content = b"test data"
    r = client.post(
        '/api/v1/convert/file/hash',
        files={'file': ('test.txt', BytesIO(test_content))}
    )
    assert r.status_code == 200
    data = r.json()
    assert 'sha256' in data
    assert len(data['sha256']) == 64


def test_csv_to_json(client):
    """Test CSV to JSON conversion."""
    from io import BytesIO
    csv_data = b"name,age\nJohn,30\nJane,25"
    r = client.post(
        '/api/v1/convert/data/csv-to-json',
        files={'file': ('data.csv', BytesIO(csv_data))}
    )
    assert r.status_code == 200
    assert r.headers['content-type'] == 'application/json'


def test_json_to_csv(client):
    """Test JSON to CSV conversion."""
    from io import BytesIO
    json_data = b'[{"name":"John","age":30},{"name":"Jane","age":25}]'
    r = client.post(
        '/api/v1/convert/data/json-to-csv',
        files={'file': ('data.json', BytesIO(json_data))}
    )
    assert r.status_code == 200
