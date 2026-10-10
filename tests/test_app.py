import pytest
import io
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
    
    # Check SPA route responses
    home_res = client.get("/home.html")
    assert home_res.status_code == 200

    index_res = client.get("/index.html")
    assert index_res.status_code == 200

    login_res = client.get("/login.html")
    assert login_res.status_code == 200
    
    signup_res = client.get("/signup.html")
    assert signup_res.status_code == 200

    arch_res = client.get("/architecture.html")
    assert arch_res.status_code == 200

    slides_res = client.get("/slides.html")
    assert slides_res.status_code == 200
    
    css_res = client.get("/style.css")
    assert css_res.status_code == 200
    
    js_res = client.get("/frontend/app.js")
    assert js_res.status_code == 200

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

def test_forgot_and_reset_password():
    # Forgot Password
    fp_res = client.post("/api/auth/forgot-password", json={"email": "karthik@ecotrack.org"})
    assert fp_res.status_code == 200
    assert "reset_link" in fp_res.json()
    token = fp_res.json()["reset_link"].split("token=")[1]

    # Reset Password
    rp_res = client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "newuserpass123"
    })
    assert rp_res.status_code == 200

    # Login with new password
    login_res = client.post("/api/auth/login", json={
        "email": "karthik@ecotrack.org",
        "password": "newuserpass123"
    })
    assert login_res.status_code == 200

    # Reset password back to user123
    fp_res2 = client.post("/api/auth/forgot-password", json={"email": "karthik@ecotrack.org"})
    token2 = fp_res2.json()["reset_link"].split("token=")[1]
    client.post("/api/auth/reset-password", json={"token": token2, "new_password": "user123"})

def test_file_upload():
    # Create 1x1 dummy PNG image
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    
    file = ("test_image.png", io.BytesIO(png_bytes), "image/png")
    upload_res = client.post("/api/upload", files={"file": file})
    assert upload_res.status_code == 200
    assert "url" in upload_res.json()
    assert upload_res.json()["url"].startswith("/uploads/")

    # Test invalid extension
    invalid_file = ("script.exe", io.BytesIO(b"binary"), "application/octet-stream")
    fail_res = client.post("/api/upload", files={"file": invalid_file})
    assert fail_res.status_code == 400

def test_user_profile_and_leaderboard():
    login_res = client.post("/api/auth/login", json={
        "email": "karthik@ecotrack.org",
        "password": "user123"
    })
    token = login_res.json()["token"]
    user_id = login_res.json()["user"]["id"]

    # Update profile
    upd_res = client.put("/api/users/profile", json={
        "full_name": "Karthik Pai Eco",
        "bio": "Updated eco warrior bio",
        "location": "Mangalore, Karnataka"
    }, headers={"Authorization": f"Bearer {token}"})
    assert upd_res.status_code == 200
    assert upd_res.json()["user"]["full_name"] == "Karthik Pai Eco"

    # Leaderboard
    lb_res = client.get("/api/users/leaderboard")
    assert lb_res.status_code == 200
    assert isinstance(lb_res.json(), list)
    assert len(lb_res.json()) > 0

    # Public Profile
    pub_res = client.get(f"/api/users/{user_id}")
    assert pub_res.status_code == 200
    assert pub_res.json()["username"] == "karthik_eco"

def test_waste_report_creation_filtering_and_admin_status():
    # Login user
    login_res = client.post("/api/auth/login", json={"email": "karthik@ecotrack.org", "password": "user123"})
    token = login_res.json()["token"]

    # Create Report
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
    report_id = data["report_id"]

    # Filter Reports
    list_res = client.get("/api/reports?category=Plastic&status=Reported")
    assert list_res.status_code == 200
    assert any(r["id"] == report_id for r in list_res.json())

    # Nearby Reports
    nearby_res = client.get("/api/reports/nearby")
    assert nearby_res.status_code == 200

    # Admin Login & Status Update
    admin_login = client.post("/api/auth/login", json={"email": "admin@ecotrack.org", "password": "admin123"})
    admin_token = admin_login.json()["token"]

    status_res = client.patch(f"/api/reports/{report_id}/status", json={
        "status": "Resolved",
        "admin_notes": "Cleanup team dispatched and area cleared."
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert status_res.status_code == 200
    assert "updated" in status_res.json()["message"]

def test_post_creation_like_comment_report():
    login_res = client.post("/api/auth/login", json={"email": "karthik@ecotrack.org", "password": "user123"})
    token = login_res.json()["token"]

    # Create post
    post_res = client.post("/api/posts", json={
        "title": "Zero Waste Workshop",
        "content": "Join our weekly workshop on zero waste composting!",
        "category": "Awareness"
    }, headers={"Authorization": f"Bearer {token}"})
    assert post_res.status_code == 200
    post_id = post_res.json()["post_id"]

    # Get Post list and detail
    posts_res = client.get("/api/posts?category=Awareness")
    assert posts_res.status_code == 200

    detail_res = client.get(f"/api/posts/{post_id}")
    assert detail_res.status_code == 200

    # Like post
    like_res = client.post(f"/api/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    assert like_res.status_code == 200
    assert like_res.json()["liked"] is True

    # Add comment
    cmt_res = client.post(f"/api/posts/{post_id}/comment", json={"comment": "Count me in!"}, headers={"Authorization": f"Bearer {token}"})
    assert cmt_res.status_code == 200

    # Report post
    rpt_res = client.post(f"/api/posts/{post_id}/report", json={"reason": "Spam content test"}, headers={"Authorization": f"Bearer {token}"})
    assert rpt_res.status_code == 200

def test_cleanup_event_lifecycle_and_attendance():
    login_res = client.post("/api/auth/login", json={"email": "karthik@ecotrack.org", "password": "user123"})
    token = login_res.json()["token"]
    user_id = login_res.json()["user"]["id"]

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

    # Get My Events
    my_evt_res = client.get("/api/events/my-events", headers={"Authorization": f"Bearer {token}"})
    assert my_evt_res.status_code == 200

    # Mark attendance
    att_res = client.post(f"/api/events/{evt_id}/attendance", json={"user_id": user_id, "attended": True}, headers={"Authorization": f"Bearer {token}"})
    assert att_res.status_code == 200

    # Submit Recap
    recap_res = client.post(f"/api/events/{evt_id}/recap", json={
        "actual_participants": 15,
        "waste_collected_kg": 75.5,
        "waste_types_collected": "Plastic, Glass, Fishing Nets"
    }, headers={"Authorization": f"Bearer {token}"})
    assert recap_res.status_code == 200

def test_notifications_and_search():
    login_res = client.post("/api/auth/login", json={"email": "karthik@ecotrack.org", "password": "user123"})
    token = login_res.json()["token"]

    # Global search
    search_res = client.get("/api/search?query=Panambur")
    assert search_res.status_code == 200
    assert "posts" in search_res.json()
    assert "events" in search_res.json()

    # Get notifications
    notif_res = client.get("/api/notifications", headers={"Authorization": f"Bearer {token}"})
    assert notif_res.status_code == 200

    # Mark all notifications read
    read_res = client.post("/api/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert read_res.status_code == 200

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

def test_admin_authorization_and_user_block():
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

    # Users list
    users_res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_res.status_code == 200
    users = users_res.json()
    demo_user = next(u for u in users if u["username"] == "karthik_eco")

    # Toggle Block User
    block_res = client.post(f"/api/admin/users/{demo_user['id']}/block", headers={"Authorization": f"Bearer {admin_token}"})
    assert block_res.status_code == 200
    assert block_res.json()["is_blocked"] is True

    # Try login as blocked user
    fail_login = client.post("/api/auth/login", json={"email": "karthik@ecotrack.org", "password": "user123"})
    assert fail_login.status_code == 403

    # Unblock User
    unblock_res = client.post(f"/api/admin/users/{demo_user['id']}/block", headers={"Authorization": f"Bearer {admin_token}"})
    assert unblock_res.status_code == 200
    assert unblock_res.json()["is_blocked"] is False

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
