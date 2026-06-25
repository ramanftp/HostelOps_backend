from modules.owner import routes as owner_routes

from fastapi.testclient import TestClient
from modules.main import app


test_client = TestClient(app)
owner_token =  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODQ3OTMwMDQsInN1YiI6Ijk5NjYyNjcxNzgiLCJpYXQiOjE3ODIyMDEwMDQsIm93bmVyX2lkIjo2fQ.XXFhgUJy0eNvEtRaVWNkQImtyQHL33H_5WQYzOwtC5g"


def test_get_rooms():
    response = test_client.get("/12/rooms",headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_room():
    room_data = {
        "name": "Test Room",
        "hostel_id": 1,
        "capacity": 4,
        "photos_urls": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "facilities": [
            2,3,4
        ]
    }

           
    response = test_client.post("/owner/rooms", json=room_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 201
    assert response.json()["name"] == room_data["name"]
    assert response.json()["hostel_id"] == room_data["hostel_id"]
    assert response.json()["capacity"] == room_data["capacity"]
    assert response.json()["facilities"] == room_data["facilities"]


def test_update_room():
    # First, create a room to update
    room_data = {
        "name": "Test Room",
        "description": "This is a test room",
        "hostel_id": 1,
        "capacity": 4,
        "photos_urls": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "facilities": [
            2,3,4
        ]
    }
    create_response = test_client.post("/owner/rooms", json=room_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert create_response.status_code == 201
    room_id = create_response.json()["id"]

    # Now, update the room
    updated_room_data = {
        "name": "Updated Test Room",
        "description": "This is an updated test room",
        "capacity": 6,
        "facilities": [
            2,3
        ]
    }
    update_response = test_client.patch(f"/owner/rooms/{room_id}", json=updated_room_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == updated_room_data["name"]
    assert update_response.json()["description"] == updated_room_data["description"]
    assert update_response.json()["capacity"] == updated_room_data["capacity"]
    assert update_response.json()["facilities"] == updated_room_data["facilities"]