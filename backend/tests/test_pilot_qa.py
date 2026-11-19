"""Pilot isolation check on the disposable local database only."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from test_bookings import setup
from test_postgres import ADMIN_URL, client_for
from test_postgres import database as database  # noqa: PLC0414

pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="PostgreSQL local não configurado")


def test_five_professionals_book_same_time_and_phone_without_sharing_clients(database):
    owners = [uuid4() for _ in range(5)]
    prepared = []
    for index, owner in enumerate(owners):
        with client_for(database, owner, address=f"pilot-{index}") as client:
            tenant, _, data = setup(client)
            prepared.append((owner, tenant, {**data, "name": f"Cliente piloto {index}"}))

    def book(item):
        owner, tenant, data = item
        with client_for(database, owner, address=str(owner)) as client:
            response = client.post(f"/api/v1/public/{tenant}/appointments", json=data)
            assert response.status_code == 201, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=5) as pool:
        booked = list(pool.map(book, prepared))
    assert len({item["id"] for item in booked}) == 5
    for index, (owner, _, data) in enumerate(prepared):
        with client_for(database, owner, address=str(owner)) as client:
            clients = client.get("/api/v1/me/clients").json()
            assert clients["total"] == 1
            assert clients["items"][0]["name"] == f"Cliente piloto {index}"
            appointments = client.get(
                "/api/v1/me/appointments", params={"start": data["day"], "end": data["day"]}
            ).json()["items"]
            assert len(appointments) == 1
            assert appointments[0]["id"] == booked[index]["id"]
            own_history = client.get(
                f"/api/v1/me/clients/{appointments[0]['client_id']}/history"
            )
            assert own_history.status_code == 200
