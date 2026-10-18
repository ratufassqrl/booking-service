import os

# Тесты используют отдельную SQLite-базу в памяти.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.db as db  # noqa: E402

# Одна общая in-memory база на все соединения теста
db.engine = db.create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
db.SessionLocal.configure(bind=db.engine)

import app.main as main  # noqa: E402

main.engine = db.engine


@pytest.fixture()
def client():
    db.Base.metadata.drop_all(db.engine)
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def room(client):
    return client.post("/rooms", json={"name": "101", "capacity": 2}).json()


def book(client, room_id, check_in, check_out, guest="Иван"):
    return client.post(
        "/bookings",
        json={"room_id": room_id, "guest_name": guest, "check_in": check_in, "check_out": check_out},
    )


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_version(client):
    assert "version" in client.get("/version").json()


def test_create_and_list_rooms(client, room):
    assert room["id"] == 1
    assert client.get("/rooms").json() == [room]


def test_duplicate_room_name(client, room):
    r = client.post("/rooms", json={"name": "101", "capacity": 3})
    assert r.status_code == 409


def test_create_booking(client, room):
    r = book(client, room["id"], "2026-11-01", "2026-11-05")
    assert r.status_code == 201
    booking = r.json()
    assert client.get(f"/bookings/{booking['id']}").json() == booking


def test_overlapping_booking_rejected(client, room):
    assert book(client, room["id"], "2026-11-01", "2026-11-05").status_code == 201
    r = book(client, room["id"], "2026-11-04", "2026-11-08", guest="Пётр")
    assert r.status_code == 409


def test_back_to_back_bookings_allowed(client, room):
    assert book(client, room["id"], "2026-11-01", "2026-11-05").status_code == 201
    assert book(client, room["id"], "2026-11-05", "2026-11-07").status_code == 201


def test_invalid_dates(client, room):
    assert book(client, room["id"], "2026-11-05", "2026-11-01").status_code == 422


def test_unknown_room(client):
    assert book(client, 999, "2026-11-01", "2026-11-02").status_code == 404


def test_cancel_booking(client, room):
    booking_id = book(client, room["id"], "2026-11-01", "2026-11-05").json()["id"]
    assert client.delete(f"/bookings/{booking_id}").status_code == 204
    assert client.get(f"/bookings/{booking_id}").status_code == 404


def test_debug_error_returns_500(client):
    assert client.get("/debug/error").status_code == 500
