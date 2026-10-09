import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import init_db, get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_health_and_root():
    response = client.get("/")
    assert response.status_code == 200

def test_user_registration_and_login():
    import uuid
    uid = uuid.uuid4().hex[:6]
    email = f"test_{uid}@ecotrack.org"
    username = f"user_{uid}"
    
    # Register
    reg_res = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": "Password123!",
        "full_name": "Test User",
        "location": "Mangalore",
        "bio": "Testing user"
    })
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert "token" in data
    assert data["user"]["points"] >= 10

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["token"]

    # Profile Me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

def test_google_authentication():
    # Test Google Login disallowed when account not yet created
    g_res_disallowed = client.post("/api/auth/google", json={
        "email": "unregistered.user@gmail.com",
        "full_name": "Unregistered User",
        "allow_create": False
    })
    assert g_res_disallowed.status_code == 404
    assert "Please create an account" in g_res_disallowed.json()["detail"]

    # Test Google Sign-Up for new user (allow_create=True)
    g_res = client.post("/api/auth/google", json={
        "email": "karthik.google@ecotrack.org",
        "full_name": "Karthik Pai Google",
        "profile_pic": "https://lh3.googleusercontent.com/a/default-user"
    })
    assert g_res.status_code == 200
    data = g_res.json()
    assert "token" in data
    assert data["user"]["full_name"] == "Karthik Pai Google"

    # Re-login with Google from login page (allow_create=False for existing user)
    g_res2 = client.post("/api/auth/google", json={
        "email": "karthik.google@ecotrack.org",
        "full_name": "Karthik Pai Google",
        "allow_create": False
    })
    assert g_res2.status_code == 200
    assert "token" in g_res2.json()

def test_waste_report_creation_and_status():
    # Login as demo user
    login_res = client.post("/api/auth/login", json={
        "email": "karthik@ecotrack.org",
        "password": "user123"
    })
    token = login_res.json()["token"]

    report_res = client.post("/api/reports", json={
        "title": "Plastic Bottle Trash Pile",
        "description": "Large accumulation of plastic waste near storm drain.",
        "category": "Plastic",
        "severity": "High",
        "location_address": "Panambur Beach Road"
    }, headers={"Authorization": f"Bearer {token}"})

    assert report_res.status_code == 200
    data = report_res.json()
    assert "tracking_id" in data
    assert data["tracking_id"].startswith("REP-")

def test_post_creation_like_comment():
    login_res = client.post("/api/auth/login", json={
        "email": "karthik@ecotrack.org",
        "password": "user123"
    })
    token = login_res.json()["token"]

    # Create post
    post_res = client.post("/api/posts", json={
        "title": "Zero Waste Workshop",
        "content": "Join our weekly workshop on zero waste composting!",
        "category": "Awareness"
    }, headers={"Authorization": f"Bearer {token}"})
    assert post_res.status_code == 200
    post_id = post_res.json()["post_id"]

    # Like post
    like_res = client.post(f"/api/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    assert like_res.status_code == 200

    # Add comment
    cmt_res = client.post(f"/api/posts/{post_id}/comment", json={"comment": "Count me in!"}, headers={"Authorization": f"Bearer {token}"})
    assert cmt_res.status_code == 200

def test_cleanup_event_lifecycle():
    login_res = client.post("/api/auth/login", json={
        "email": "karthik@ecotrack.org",
        "password": "user123"
    })
    token = login_res.json()["token"]

    # Create Event
    evt_res = client.post("/api/events", json={
        "name": "Panambur Beach Clean Drive",
        "description": "Cleaning marine plastic waste.",
        "event_date": "2026-11-20",
        "start_time": "08:00 AM",
        "end_time": "11:00 AM",
        "location_address": "Panambur Beach",
        "max_participants": 40
    }, headers={"Authorization": f"Bearer {token}"})
    assert evt_res.status_code == 200
    evt_id = evt_res.json()["event_id"]

    # Detail
    detail_res = client.get(f"/api/events/{evt_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Panambur Beach Clean Drive"

def test_ai_services():
    # Improve post
    ai_post = client.post("/api/ai/improve-post", json={
        "content": "we must stop dumping plastic bags into storm drains",
        "title": "stop plastic pollution"
    })
    assert ai_post.status_code == 200
    assert "Stop Plastic Pollution" in ai_post.json()["title"]

    # Suggest description
    ai_desc = client.post("/api/ai/suggest-description", json={
        "category": "Plastic",
        "location": "Central Market"
    })
    assert ai_desc.status_code == 200
    assert "plastic" in ai_desc.json()["description"].lower()

    # EcoBot Chat
    ai_chat = client.post("/api/ai/chat", json={"query": "How do I recycle plastic?"})
    assert ai_chat.status_code == 200
    assert "Plastic" in ai_chat.json()["reply"]

    # Impact Calculator
    ai_impact = client.post("/api/ai/calculate-impact", json={"waste_kg": 100, "category": "Plastic"})
    assert ai_impact.status_code == 200
    assert ai_impact.json()["co2_saved_kg"] > 0

    # Event Optimizer
    ai_opt = client.post("/api/ai/optimize-event", json={"location": "Beach", "waste_category": "Plastic", "estimated_area_sqm": 500})
    assert ai_opt.status_code == 200
    assert ai_opt.json()["recommended_volunteers"] > 0

    # Cleanliness Index & Green Route Optimizer
    ai_idx = client.get("/api/ai/cleanliness-index")
    assert ai_idx.status_code == 200
    assert "cleanliness_score" in ai_idx.json()
    assert "green_route_recommendation" in ai_idx.json()

def test_admin_authorization():
    # Admin Login
    admin_res = client.post("/api/auth/login", json={
        "email": "admin@ecotrack.org",
        "password": "admin123"
    })
    admin_token = admin_res.json()["token"]

    # Stats
    stats_res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert stats_res.status_code == 200
    assert "total_users" in stats_res.json()

def test_post_edit_delete_and_certificate():
    login_res = client.post("/api/auth/login", json={
        "email": "karthik@ecotrack.org",
        "password": "user123"
    })
    token = login_res.json()["token"]
    user_id = login_res.json()["user"]["id"]

    # Create post
    post_res = client.post("/api/posts", json={"title": "Original Title", "content": "Original content"}, headers={"Authorization": f"Bearer {token}"})
    post_id = post_res.json()["post_id"]

    # Edit post
    put_res = client.put(f"/api/posts/{post_id}", json={"title": "Updated Title", "content": "Updated content", "category": "Awareness"}, headers={"Authorization": f"Bearer {token}"})
    assert put_res.status_code == 200

    # Delete post
    del_res = client.delete(f"/api/posts/{post_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

    # Event Creation, Certificate Generation & Deletion
    evt_res = client.post("/api/events", json={
        "name": "Temporary Event To Delete",
        "description": "Short description",
        "event_date": "2026-12-01",
        "start_time": "09:00 AM",
        "end_time": "11:00 AM",
        "location_address": "Test Site"
    }, headers={"Authorization": f"Bearer {token}"})
    assert evt_res.status_code == 200
    evt_id = evt_res.json()["event_id"]

    # Certificate test on created event
    cert_res = client.get(f"/api/events/{evt_id}/certificate/{user_id}")
    assert cert_res.status_code == 200
    assert "certificate_id" in cert_res.json()

    del_evt = client.delete(f"/api/events/{evt_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_evt.status_code == 200


