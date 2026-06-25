from modules.owner import routes as owner_routes

from fastapi.testclient import TestClient
from modules.main import app


test_client = TestClient(app)
owner_token =  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODQ3OTMwMDQsInN1YiI6Ijk5NjYyNjcxNzgiLCJpYXQiOjE3ODIyMDEwMDQsIm93bmVyX2lkIjo2fQ.XXFhgUJy0eNvEtRaVWNkQImtyQHL33H_5WQYzOwtC5g"
def test_get_hostels():
    response = test_client.get("/owner/hostels",headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_hostel():
    hostel_data = {
        "name": "Test Hostel",
        "description": "This is a test hostel",
        "address": "123 Test Street",
        "city": "Test City",
        "state": "Test State",
        "country": "Test Country",
        "zipcode": "12345",
        "owner_id": 6,
        "photos_urls": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "bank_account_number": "1234567890",
        "bank_ifsc_code": "TEST0001234",
        "bank_name": "Test Bank",
        "category": 1,
        "bank_account_holder_name": "John Doe",
        "upi_id": "test@upi",
        "is_cash": True,
        "facilities": [
            2,3,4
        ]

    }

           
    response = test_client.post("/owner/hostels", json=hostel_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 201
    assert response.json()["name"] == hostel_data["name"]
    assert response.json()["address"] == hostel_data["address"]
    assert response.json()["owner_id"] == hostel_data["owner_id"]
    assert response.json()["photos_urls"] == hostel_data["photos_urls"]
    assert response.json()["bank_account_number"] == hostel_data["bank_account_number"]
    assert response.json()["bank_ifsc_code"] == hostel_data["bank_ifsc_code"]
    assert response.json()["bank_name"] == hostel_data["bank_name"]
    assert response.json()["category"] == hostel_data["category"]   
    assert response.json()["bank_account_holder_name"] == hostel_data["bank_account_holder_name"]
    assert response.json()["upi_id"] == hostel_data["upi_id"]
    assert response.json()["is_cash"] == hostel_data["is_cash"]
    assert response.json()["facilities"] == hostel_data["facilities"]
    assert response.json()["city"] == hostel_data["city"]
    assert response.json()["state"] == hostel_data["state"]
    assert response.json()["country"] == hostel_data["country"]
    assert response.json()["zipcode"] == hostel_data["zipcode"]


def test_update_hostel():
    # First, create a hostel to update
    hostel_data = {
        "name": "Test Hostel for Update",
        "description": "This is a test hostel for update",
        "address": "123 Test Street",
        "city": "Test City",
        "state": "Test State",
        "country": "Test Country",
        "zipcode": "12345",
        "owner_id": 6,
        "photos_urls": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "bank_account_number": "1234567890",
        "bank_ifsc_code": "TEST0001234",
        "bank_name": "Test Bank",
        "category": 1,
        "bank_account_holder_name": "John Doe",
        "upi_id": "test@upi",
        "is_cash": True,
        "facilities": [
            2,3,4
        ]
    }
    create_response = test_client.post("/owner/hostels", json=hostel_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert create_response.status_code == 201
    hostel_id = create_response.json()["id"]

    # Now, update the hostel
    updated_hostel_data = {
        "name": "Updated Test Hostel",
        "description": "This is an updated test hostel",
        # ... other fields can be updated as needed
    }
    update_response = test_client.patch(f"/owner/hostels/{hostel_id}", json=updated_hostel_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == updated_hostel_data["name"]
    assert update_response.json()["description"] == updated_hostel_data["description"]


def test_delete_hostel():
    # First, create a hostel to delete
    hostel_data = {
        "name": "Test Hostel for Deletion",
        "description": "This is a test hostel for deletion",
        "address": "123 Test Street",
        "city": "Test City",
        "state": "Test State",
        "country": "Test Country",
        "zipcode": "12345",
        "owner_id": 6,
        "photos_urls": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "bank_account_number": "1234567890",
        "bank_ifsc_code": "TEST0001234",
        "bank_name": "Test Bank",
        "category": 1,
        "bank_account_holder_name": "John Doe",
        "upi_id": "test@upi",
        "is_cash": True,
        "facilities": [
            2,3,4
        ]
    }
    create_response = test_client.post("/owner/hostels", json=hostel_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert create_response.status_code == 201
    hostel_id = create_response.json()["id"]

    # Now, delete the hostel
    delete_response = test_client.delete(f"/owner/hostels/{hostel_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert delete_response.status_code == 204

    # Verify that the hostel has been deleted
    get_response = test_client.get(f"/owner/hostels/{hostel_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert get_response.status_code == 404