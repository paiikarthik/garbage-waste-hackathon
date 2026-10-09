import os
import sys
import random
import uuid
import sqlite3
from typing import Optional, List
from pathlib import Path

# Ensure root project directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr

from backend.db import get_db, init_db, hash_password
from backend.auth import (
    create_access_token, 
    get_current_user, 
    get_optional_current_user, 
    get_admin_user, 
    generate_reset_token
)
from backend.ai_service import (
    classify_waste_image, 
    improve_post_with_ai, 
    suggest_waste_description,
    answer_eco_chat,
    calculate_environmental_impact,
    optimize_cleanup_event,
    calculate_neighborhood_cleanliness_index
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize database on startup
init_db()

app = FastAPI(
    title="EcoTrack - Smart Waste Management & Community Cleanliness Platform",
    description="Full-stack API for reporting waste, community cleanup events, AI waste classification, social feed, and gamification.",
    version="2.0.0"
)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Serve uploaded static images
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# --- Helper Functions ---

def award_points(cursor, user_id: int, points: int, reason: str):
    """Adds contribution points to user, logs audit trail, and grants earned badges."""
    cursor.execute("UPDATE users SET points = points + ? WHERE id = ?", (points, user_id))
    cursor.execute("INSERT INTO points_log (user_id, points, reason) VALUES (?, ?, ?)", (user_id, points, reason))
    
    # Check total points to award milestone badges
    cursor.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        user_points = row["points"]
        cursor.execute("SELECT code, points_required FROM badges WHERE points_required <= ?", (user_points,))
        earned = cursor.fetchall()
        for b in earned:
            cursor.execute("""
                INSERT OR IGNORE INTO user_badges (user_id, badge_code) 
                VALUES (?, ?)
            """, (user_id, b["code"]))

def send_notification(cursor, user_id: int, title: str, message: str, notif_type: str = "info", link: str = "#"):
    """Inserts real-time user notification into DB."""
    cursor.execute("""
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, title, message, notif_type, link))

# --- Pydantic Schemas ---

class RegisterSchema(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    location: Optional[str] = "Mangalore, India"
    bio: Optional[str] = "Environment enthusiast"

class LoginSchema(BaseModel):
    email: str
    password: str

class GoogleAuthSchema(BaseModel):
    email: str
    full_name: Optional[str] = None
    profile_pic: Optional[str] = None
    allow_create: Optional[bool] = True

class ForgotPasswordSchema(BaseModel):
    email: str

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

class UserProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    profile_pic: Optional[str] = None

class ReportCreateSchema(BaseModel):
    title: str
    description: str
    category: str
    severity: str
    location_address: str
    latitude: Optional[float] = 12.9141
    longitude: Optional[float] = 74.8560
    image_url: Optional[str] = None

class ReportStatusUpdateSchema(BaseModel):
    status: str
    admin_notes: Optional[str] = None

class PostCreateSchema(BaseModel):
    title: Optional[str] = None
    content: str
    category: Optional[str] = "Awareness"
    image_url: Optional[str] = None
    location: Optional[str] = None

class PostCommentSchema(BaseModel):
    comment: str

class PostReportSchema(BaseModel):
    reason: str

class EventCreateSchema(BaseModel):
    name: str
    description: str
    cover_image: Optional[str] = None
    event_date: str
    start_time: str
    end_time: str
    location_address: str
    latitude: Optional[float] = 12.9141
    longitude: Optional[float] = 74.8560
    max_participants: Optional[int] = 50
    waste_category: Optional[str] = "Mixed"
    required_materials: Optional[str] = None

class EventRecapSchema(BaseModel):
    before_image: Optional[str] = None
    after_image: Optional[str] = None
    actual_participants: int
    waste_collected_kg: float
    waste_types_collected: str

class PostUpdateSchema(BaseModel):
    title: Optional[str] = None
    content: str
    category: Optional[str] = "Awareness"
    image_url: Optional[str] = None
    location: Optional[str] = None

class AttendanceSchema(BaseModel):
    user_id: int
    attended: bool

class AIPostImproveSchema(BaseModel):
    content: str
    title: Optional[str] = ""

class AISuggestDescSchema(BaseModel):
    category: str
    location: Optional[str] = ""

class AIChatSchema(BaseModel):
    query: str

class AIImpactSchema(BaseModel):
    waste_kg: float
    category: Optional[str] = "Mixed"

class AIOptimizeEventSchema(BaseModel):
    location: str
    waste_category: str
    estimated_area_sqm: Optional[int] = 500

# --- File Upload Endpoint ---

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Uploads an image file to server uploads directory."""
    try:
        ext = Path(file.filename).suffix.lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP, and GIF images are allowed.")
        
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = UPLOAD_DIR / filename
        
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds maximum limit of 10MB.")
        
        with open(filepath, "wb") as f:
            f.write(contents)
        
        return {
            "status": "success",
            "filename": filename,
            "url": f"/uploads/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# --- Authentication Routes ---

@app.post("/api/auth/register")
def register(data: RegisterSchema):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ? OR username = ?", (data.email, data.username))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email or Username is already registered.")
    
    hashed = hash_password(data.password)
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name, bio, location, points)
        VALUES (?, ?, ?, ?, ?, ?, 10)
    """, (data.username, data.email, hashed, data.full_name, data.bio, data.location))
    conn.commit()
    user_id = cursor.lastrowid
    
    # Award welcome points & badge
    award_points(cursor, user_id, 0, "Registration Welcome Bonus")
    cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'eco_beginner')", (user_id,))
    send_notification(cursor, user_id, "Welcome to EcoTrack!", "You've earned 10 points and the Eco Beginner badge.", "badge", "#profile")
    conn.commit()
    conn.close()
    
    token = create_access_token(user_id, "user", data.username)
    return {
        "status": "success",
        "message": "Registration successful!",
        "token": token,
        "user": {
            "id": user_id,
            "username": data.username,
            "email": data.email,
            "full_name": data.full_name,
            "role": "user",
            "points": 10
        }
    }

@app.post("/api/auth/login")
def login(data: LoginSchema):
    conn = get_db()
    cursor = conn.cursor()
    
    hashed = hash_password(data.password)
    cursor.execute("SELECT id, username, email, full_name, role, points, is_blocked FROM users WHERE email = ? AND password_hash = ?", (data.email, hashed))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
    if user["is_blocked"]:
        raise HTTPException(status_code=403, detail="Your account has been suspended by an administrator.")
    
    token = create_access_token(user["id"], user["role"], user["username"])
    return {
        "status": "success",
        "message": "Login successful!",
        "token": token,
        "user": dict(user)
    }

@app.post("/api/auth/google")
def google_auth(data: GoogleAuthSchema):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT id, username, email, full_name, role, points, is_blocked, profile_pic FROM users WHERE email = ?", (data.email,))
    user = cursor.fetchone()
    
    if user:
        if user["is_blocked"]:
            conn.close()
            raise HTTPException(status_code=403, detail="Your account has been suspended by an administrator.")
            
        user_id = user["id"]
        username = user["username"]
        role = user["role"]
        
        # Update full_name if empty or default
        updates = []
        params = []
        if data.full_name and (not user["full_name"] or user["full_name"] == "Google Eco User" or user["full_name"].startswith("user_")):
            updates.append("full_name = ?")
            params.append(data.full_name)
        if data.profile_pic and not user["profile_pic"]:
            updates.append("profile_pic = ?")
            params.append(data.profile_pic)
            
        if updates:
            params.append(user_id)
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
    else:
        if not data.allow_create:
            conn.close()
            raise HTTPException(status_code=404, detail="No account found with this Google email. Please create an account on the Sign Up page first.")

        # Register new Google User
        clean_name = data.full_name or data.email.split('@')[0].title()
        username = data.email.split('@')[0] + "_g"
        hashed = hash_password(f"GoogleAuth_{uuid.uuid4().hex}")
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, profile_pic, points)
            VALUES (?, ?, ?, ?, ?, 10)
        """, (username, data.email, hashed, clean_name, data.profile_pic))
        conn.commit()
        user_id = cursor.lastrowid
        role = "user"
        
        award_points(cursor, user_id, 0, "Registration Welcome Bonus")
        cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'eco_beginner')", (user_id,))
        send_notification(cursor, user_id, "Welcome to EcoTrack!", "You've earned 10 points and the Eco Beginner badge.", "badge", "#profile")
        conn.commit()

    # Retrieve full user profile object
    cursor.execute("SELECT id, username, email, full_name, profile_pic, role, points FROM users WHERE id = ?", (user_id,))
    updated_user = dict(cursor.fetchone())
    conn.close()
    
    token = create_access_token(user_id, role, username)
    return {
        "status": "success",
        "message": "Google Authentication successful!",
        "token": token,
        "user": updated_user
    }

@app.post("/api/auth/forgot-password")
def forgot_password(data: ForgotPasswordSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (data.email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=444 if False else 404, detail="No account found with this email.")
    
    token = generate_reset_token()
    cursor.execute("UPDATE users SET reset_token = ? WHERE id = ?", (token, user["id"]))
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "message": "Password reset token generated! Check your email instructions.",
        "reset_link": f"/reset-password?token={token}"
    }

@app.post("/api/auth/reset-password")
def reset_password(data: ResetPasswordSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE reset_token = ?", (data.token,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")
    
    new_hashed = hash_password(data.new_password)
    cursor.execute("UPDATE users SET password_hash = ?, reset_token = NULL WHERE id = ?", (new_hashed, user["id"]))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Password reset successfully! You can now log in."}

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch Badges
    cursor.execute("""
        SELECT b.code, b.name, b.icon, b.description, ub.earned_at
        FROM user_badges ub
        JOIN badges b ON ub.badge_code = b.code
        WHERE ub.user_id = ?
    """, (current_user["id"],))
    badges = [dict(r) for r in cursor.fetchall()]
    
    # Fetch Notifications count
    cursor.execute("SELECT COUNT(*) as unread FROM notifications WHERE user_id = ? AND is_read = 0", (current_user["id"],))
    unread_notifs = cursor.fetchone()["unread"]
    
    conn.close()
    
    res = dict(current_user)
    res["badges"] = badges
    res["unread_notifications"] = unread_notifs
    return res

# --- User Profile & Leaderboard Routes ---

@app.put("/api/users/profile")
def update_profile(data: UserProfileUpdateSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    params = []
    if data.full_name is not None:
        updates.append("full_name = ?")
        params.append(data.full_name)
    if data.bio is not None:
        updates.append("bio = ?")
        params.append(data.bio)
    if data.location is not None:
        updates.append("location = ?")
        params.append(data.location)
    if data.profile_pic is not None:
        updates.append("profile_pic = ?")
        params.append(data.profile_pic)
    
    if updates:
        params.append(current_user["id"])
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    
    cursor.execute("SELECT id, username, email, full_name, bio, location, profile_pic, points, role FROM users WHERE id = ?", (current_user["id"],))
    updated_user = dict(cursor.fetchone())
    conn.close()
    return {"status": "success", "user": updated_user}

@app.get("/api/users/leaderboard")
def get_leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.full_name, u.profile_pic, u.location, u.points, u.role,
               (SELECT COUNT(*) FROM waste_reports WHERE user_id = u.id) as reports_count,
               (SELECT COUNT(*) FROM event_participants WHERE user_id = u.id) as events_joined_count,
               (SELECT COUNT(*) FROM events WHERE organizer_id = u.id) as events_organized_count
        FROM users u
        WHERE u.is_blocked = 0
        ORDER BY u.points DESC, reports_count DESC
        LIMIT 50
    """)
    users = [dict(r) for r in cursor.fetchall()]
    
    # Attach Badges to each top user
    for u in users:
        cursor.execute("""
            SELECT b.code, b.name, b.icon
            FROM user_badges ub
            JOIN badges b ON ub.badge_code = b.code
            WHERE ub.user_id = ?
        """, (u["id"],))
        u["badges"] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return users

@app.get("/api/users/{user_id}")
def get_user_public_profile(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, full_name, bio, location, profile_pic, points, created_at,
               (SELECT COUNT(*) FROM waste_reports WHERE user_id = users.id) as total_reports,
               (SELECT COUNT(*) FROM posts WHERE user_id = users.id) as total_posts,
               (SELECT COUNT(*) FROM event_participants WHERE user_id = users.id) as events_joined,
               (SELECT COUNT(*) FROM events WHERE organizer_id = users.id) as events_organized
        FROM users WHERE id = ? AND is_blocked = 0
    """, (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User profile not found.")
    
    user_dict = dict(user)
    
    # Badges
    cursor.execute("""
        SELECT b.code, b.name, b.icon, b.description
        FROM user_badges ub
        JOIN badges b ON ub.badge_code = b.code
        WHERE ub.user_id = ?
    """, (user_id,))
    user_dict["badges"] = [dict(r) for r in cursor.fetchall()]
    
    # Recent Posts
    cursor.execute("""
        SELECT id, title, content, category, image_url, created_at, likes_count, comments_count
        FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT 5
    """, (user_id,))
    user_dict["recent_posts"] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return user_dict

# --- Waste Reports Routes ---

@app.post("/api/reports")
def create_waste_report(data: ReportCreateSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    tracking_id = f"REP-{random.randint(10000, 99999)}"
    cursor.execute("""
        INSERT INTO waste_reports (tracking_id, user_id, title, description, category, severity, status, image_url, location_address, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, 'Reported', ?, ?, ?, ?)
    """, (tracking_id, current_user["id"], data.title, data.description, data.category, data.severity, data.image_url, data.location_address, data.latitude, data.longitude))
    report_id = cursor.lastrowid
    
    # Gamification: +10 Points for reporting waste
    award_points(cursor, current_user["id"], 10, "Reported Waste Problem")
    
    # Grant Waste Reporter badge if first report
    cursor.execute("SELECT COUNT(*) as cnt FROM waste_reports WHERE user_id = ?", (current_user["id"],))
    if cursor.fetchone()["cnt"] == 1:
        cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'waste_reporter')", (current_user["id"],))
        send_notification(cursor, current_user["id"], "Badge Unlocked!", "You've earned the Waste Reporter badge!", "badge", "#profile")

    send_notification(cursor, current_user["id"], "Waste Report Submitted", f"Report #{tracking_id} was submitted successfully. Status: Reported.", "report", "#reports")
    
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "message": "Waste report created successfully!",
        "tracking_id": tracking_id,
        "report_id": report_id
    }

@app.get("/api/reports")
def get_waste_reports(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    severity: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[int] = None
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT r.*, u.username, u.full_name, u.profile_pic
        FROM waste_reports r
        JOIN users u ON r.user_id = u.id
        WHERE 1=1
    """
    params = []
    
    if status_filter and status_filter != 'All':
        query += " AND r.status = ?"
        params.append(status_filter)
    if category and category != 'All':
        query += " AND r.category = ?"
        params.append(category)
    if severity and severity != 'All':
        query += " AND r.severity = ?"
        params.append(severity)
    if location and location.strip():
        query += " AND r.location_address LIKE ?"
        params.append(f"%{location.strip()}%")
    if user_id:
        query += " AND r.user_id = ?"
        params.append(user_id)
    if search:
        query += " AND (r.title LIKE ? OR r.description LIKE ? OR r.location_address LIKE ? OR r.tracking_id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
        
    query += " ORDER BY r.created_at DESC"
    cursor.execute(query, params)
    reports = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return reports

@app.get("/api/reports/nearby")
def get_nearby_reports(lat: float = 12.9141, lng: float = 74.8560, radius_km: float = 10.0):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, u.username, u.full_name, u.profile_pic
        FROM waste_reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.status != 'Resolved' AND r.status != 'Rejected'
        ORDER BY r.created_at DESC LIMIT 30
    """)
    reports = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return reports

@app.get("/api/reports/{report_id}")
def get_waste_report_detail(report_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, u.username, u.full_name, u.profile_pic, u.email
        FROM waste_reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.id = ?
    """, (report_id,))
    report = cursor.fetchone()
    conn.close()
    if not report:
        raise HTTPException(status_code=404, detail="Waste report not found.")
    return dict(report)

@app.patch("/api/reports/{report_id}/status")
def update_report_status(report_id: int, data: ReportStatusUpdateSchema, current_user: dict = Depends(get_admin_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_id, tracking_id, title FROM waste_reports WHERE id = ?", (report_id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found.")
    
    cursor.execute("""
        UPDATE waste_reports 
        SET status = ?, admin_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (data.status, data.admin_notes, report_id))
    
    # Notify reporter
    send_notification(
        cursor, 
        report["user_id"], 
        f"Report #{report['tracking_id']} Updated", 
        f"Status changed to: {data.status}. " + (f"Admin note: {data.admin_notes}" if data.admin_notes else ""), 
        "report", 
        "#reports"
    )
    
    # Bonus points if resolved
    if data.status == "Resolved":
        award_points(cursor, report["user_id"], 15, f"Waste Report Resolved ({report['tracking_id']})")
        send_notification(cursor, report["user_id"], "Waste Problem Resolved!", "You earned +15 bonus points for your resolved report!", "points", "#profile")
        
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Report status updated to {data.status}."}

# --- Social Feed & Community Posts Routes ---

@app.post("/api/posts")
def create_post(data: PostCreateSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO posts (user_id, title, content, category, image_url, location)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (current_user["id"], data.title, data.content, data.category, data.image_url, data.location))
    post_id = cursor.lastrowid
    
    # Gamification: +5 points for useful awareness post
    award_points(cursor, current_user["id"], 5, "Created Community Post")
    send_notification(cursor, current_user["id"], "Post Published!", "Your community awareness post is live (+5 points).", "post", "#feed")
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Post created successfully!", "post_id": post_id}

@app.get("/api/posts")
def get_posts(
    category: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT p.*, u.username, u.full_name, u.profile_pic, u.role
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.is_flagged = 0
    """
    params = []
    
    if user_id:
        query += " AND p.user_id = ?"
        params.append(user_id)
    if category and category != 'All':
        query += " AND p.category = ?"
        params.append(category)
    if location and location.strip():
        query += " AND (p.location LIKE ? OR u.location LIKE ?)"
        loc_term = f"%{location.strip()}%"
        params.extend([loc_term, loc_term])
    if search:
        query += " AND (p.title LIKE ? OR p.content LIKE ? OR p.location LIKE ? OR u.username LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
        
    query += " ORDER BY p.created_at DESC"
    cursor.execute(query, params)
    posts = [dict(p) for p in cursor.fetchall()]
    
    # Check if liked by current user
    if current_user:
        for p in posts:
            cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (p["id"], current_user["id"]))
            p["is_liked"] = bool(cursor.fetchone())
    else:
        for p in posts:
            p["is_liked"] = False

    conn.close()
    return posts

@app.get("/api/posts/{post_id}")
def get_post_detail(post_id: int, current_user: Optional[dict] = Depends(get_optional_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.username, u.full_name, u.profile_pic, u.role, u.bio
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    """, (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found.")
    
    post_dict = dict(post)
    
    if current_user:
        cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, current_user["id"]))
        post_dict["is_liked"] = bool(cursor.fetchone())
    else:
        post_dict["is_liked"] = False
        
    # Get Comments
    cursor.execute("""
        SELECT c.*, u.username, u.full_name, u.profile_pic
        FROM post_comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.post_id = ?
        ORDER BY c.created_at ASC
    """, (post_id,))
    post_dict["comments"] = [dict(c) for c in cursor.fetchall()]
    
    conn.close()
    return post_dict

@app.put("/api/posts/{post_id}")
def update_post(post_id: int, data: PostCreateSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found.")
    
    if post["user_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="You can only edit your own posts.")
        
    cursor.execute("""
        UPDATE posts
        SET title = ?, content = ?, category = ?, image_url = ?, location = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (data.title, data.content, data.category, data.image_url, data.location, post_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Post updated successfully."}

@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found.")
        
    if post["user_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="You do not have permission to delete this post.")
        
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Post deleted successfully."}

@app.post("/api/posts/{post_id}/like")
def toggle_like_post(post_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found.")
        
    cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, current_user["id"]))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("DELETE FROM post_likes WHERE id = ?", (existing["id"],))
        cursor.execute("UPDATE posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
        liked = False
    else:
        cursor.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, current_user["id"]))
        cursor.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        liked = True
        
        # Notify Post author if different user
        if post["user_id"] != current_user["id"]:
            send_notification(cursor, post["user_id"], "New Post Like", f"{current_user['full_name']} liked your post.", "like", f"#post/{post_id}")
            
    conn.commit()
    cursor.execute("SELECT likes_count FROM posts WHERE id = ?", (post_id,))
    likes_count = cursor.fetchone()["likes_count"]
    conn.close()
    
    return {"status": "success", "liked": liked, "likes_count": likes_count}

@app.post("/api/posts/{post_id}/comment")
def add_comment(post_id: int, data: PostCommentSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found.")
        
    cursor.execute("INSERT INTO post_comments (post_id, user_id, comment) VALUES (?, ?, ?)", (post_id, current_user["id"], data.comment))
    cursor.execute("UPDATE posts SET comments_count = comments_count + 1 WHERE id = ?", (post_id,))
    
    if post["user_id"] != current_user["id"]:
        send_notification(cursor, post["user_id"], "New Comment", f"{current_user['full_name']} commented on your post.", "comment", f"#post/{post_id}")
        
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Comment added successfully."}

@app.post("/api/posts/{post_id}/report")
def report_post(post_id: int, data: PostReportSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO post_reports (post_id, user_id, reason) VALUES (?, ?, ?)", (post_id, current_user["id"], data.reason))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Post reported to moderators for review."}

@app.put("/api/posts/{post_id}")
def update_post(post_id: int, data: PostUpdateSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found.")
    if post["user_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="You can only edit your own posts.")
    
    cursor.execute("""
        UPDATE posts 
        SET title = ?, content = ?, category = ?, image_url = COALESCE(?, image_url), location = COALESCE(?, location), updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (data.title, data.content, data.category, data.image_url, data.location, post_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Post updated successfully."}

@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Post not found.")
    if post["user_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="You can only delete your own posts.")
    
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Post deleted successfully."}

# --- Cleanup Events Routes ---

@app.post("/api/events")
def create_event(data: EventCreateSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO events (organizer_id, name, description, cover_image, event_date, start_time, end_time, location_address, latitude, longitude, max_participants, waste_category, required_materials, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Upcoming')
    """, (current_user["id"], data.name, data.description, data.cover_image, data.event_date, data.start_time, data.end_time, data.location_address, data.latitude, data.longitude, data.max_participants, data.waste_category, data.required_materials))
    event_id = cursor.lastrowid
    
    # Auto join organizer
    cursor.execute("INSERT INTO event_participants (event_id, user_id) VALUES (?, ?)", (event_id, current_user["id"]))
    
    # Gamification: +50 Points for organizing cleanup event
    award_points(cursor, current_user["id"], 50, f"Organized Cleanup Event: {data.name}")
    
    # Unlock Green Warrior badge if organizer
    cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'green_warrior')", (current_user["id"],))
    send_notification(cursor, current_user["id"], "Event Created!", f"Event '{data.name}' is published (+50 points)! Green Warrior badge granted.", "event", "#events")
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Cleanup event created successfully!", "event_id": event_id}

@app.get("/api/events")
def get_events(
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    location: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT e.*, u.username as organizer_username, u.full_name as organizer_name, u.profile_pic as organizer_pic,
               (SELECT COUNT(*) FROM event_participants WHERE event_id = e.id) as participant_count
        FROM events e
        JOIN users u ON e.organizer_id = u.id
        WHERE 1=1
    """
    params = []
    
    if category and category != 'All':
        query += " AND e.waste_category = ?"
        params.append(category)
    if status_filter and status_filter != 'All':
        query += " AND e.status = ?"
        params.append(status_filter)
    if location and location.strip():
        query += " AND e.location_address LIKE ?"
        params.append(f"%{location.strip()}%")
    if search:
        query += " AND (e.name LIKE ? OR e.description LIKE ? OR e.location_address LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    query += " ORDER BY e.event_date ASC"
    cursor.execute(query, params)
    events = [dict(e) for e in cursor.fetchall()]
    
    if current_user:
        for e in events:
            cursor.execute("SELECT id FROM event_participants WHERE event_id = ? AND user_id = ?", (e["id"], current_user["id"]))
            e["is_joined"] = bool(cursor.fetchone())
    else:
        for e in events:
            e["is_joined"] = False

    conn.close()
    return events

@app.get("/api/events/my-events")
def get_my_events(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # Events Organized by User
    cursor.execute("""
        SELECT e.*, (SELECT COUNT(*) FROM event_participants WHERE event_id = e.id) as participant_count
        FROM events e WHERE e.organizer_id = ? ORDER BY e.event_date DESC
    """, (current_user["id"],))
    organized = [dict(e) for e in cursor.fetchall()]
    
    # Events Joined by User
    cursor.execute("""
        SELECT e.*, u.full_name as organizer_name, (SELECT COUNT(*) FROM event_participants WHERE event_id = e.id) as participant_count
        FROM event_participants ep
        JOIN events e ON ep.event_id = e.id
        JOIN users u ON e.organizer_id = u.id
        WHERE ep.user_id = ? AND e.organizer_id != ?
        ORDER BY e.event_date DESC
    """, (current_user["id"], current_user["id"]))
    joined = [dict(e) for e in cursor.fetchall()]
    
    conn.close()
    return {
        "organized": organized,
        "joined": joined
    }

@app.get("/api/events/{event_id}")
def get_event_detail(event_id: int, current_user: Optional[dict] = Depends(get_optional_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.*, u.username as organizer_username, u.full_name as organizer_name, u.profile_pic as organizer_pic, u.email as organizer_email, u.bio as organizer_bio,
               (SELECT COUNT(*) FROM event_participants WHERE event_id = e.id) as participant_count
        FROM events e
        JOIN users u ON e.organizer_id = u.id
        WHERE e.id = ?
    """, (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found.")
        
    event_dict = dict(event)
    
    # Participants list
    cursor.execute("""
        SELECT u.id, u.username, u.full_name, u.profile_pic, ep.status as participant_status, ep.joined_at
        FROM event_participants ep
        JOIN users u ON ep.user_id = u.id
        WHERE ep.event_id = ?
        ORDER BY ep.joined_at ASC
    """, (event_id,))
    event_dict["participants"] = [dict(p) for p in cursor.fetchall()]
    
    if current_user:
        cursor.execute("SELECT id FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, current_user["id"]))
        event_dict["is_joined"] = bool(cursor.fetchone())
    else:
        event_dict["is_joined"] = False
        
    conn.close()
    return event_dict

@app.post("/api/events/{event_id}/join")
def join_event(event_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, max_participants, organizer_id FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found.")
        
    cursor.execute("SELECT COUNT(*) as count FROM event_participants WHERE event_id = ?", (event_id,))
    cnt = cursor.fetchone()["count"]
    if cnt >= event["max_participants"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Event has reached maximum participant capacity.")
        
    try:
        cursor.execute("INSERT INTO event_participants (event_id, user_id) VALUES (?, ?)", (event_id, current_user["id"]))
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="You have already joined this event.")
        
    # Gamification: +20 points for joining cleanup event
    award_points(cursor, current_user["id"], 20, f"Joined Cleanup Event: {event['name']}")
    
    # Unlock Cleanup Volunteer badge if first event
    cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'cleanup_volunteer')", (current_user["id"],))
    
    send_notification(cursor, current_user["id"], "Event Joined!", f"You registered for '{event['name']}' (+20 points).", "event", f"#event/{event_id}")
    
    if event["organizer_id"] != current_user["id"]:
        send_notification(cursor, event["organizer_id"], "New Participant!", f"{current_user['full_name']} joined your event '{event['name']}'.", "event", f"#event/{event_id}")

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Successfully joined the cleanup event!"}

@app.post("/api/events/{event_id}/leave")
def leave_event(event_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found.")
        
    if event["organizer_id"] == current_user["id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Organizers cannot leave their own event. Use cancel event instead.")
        
    cursor.execute("DELETE FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, current_user["id"]))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "You have left the event."}

@app.post("/api/events/{event_id}/recap")
def submit_event_recap(event_id: int, data: EventRecapSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, organizer_id, name FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found.")
        
    if event["organizer_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Only the organizer can submit the event recap.")
        
    cursor.execute("""
        UPDATE events
        SET status = 'Completed',
            before_image = ?,
            after_image = ?,
            actual_participants = ?,
            waste_collected_kg = ?,
            waste_types_collected = ?
        WHERE id = ?
    """, (data.before_image, data.after_image, data.actual_participants, data.waste_collected_kg, data.waste_types_collected, event_id))
    
    # Award +30 bonus points to organizer for event completion
    award_points(cursor, current_user["id"], 30, f"Completed Event Cleanup Recap ({data.waste_collected_kg} kg waste collected)")
    
    # Notify all participants
    cursor.execute("SELECT user_id FROM event_participants WHERE event_id = ?", (event_id,))
    participants = cursor.fetchall()
    for p in participants:
        send_notification(cursor, p["user_id"], "Event Completed!", f"Recap uploaded for '{event['name']}': {data.waste_collected_kg} kg of waste collected!", "event", f"#event/{event_id}")

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Event recap submitted successfully and marked as Completed!"}

@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, organizer_id, name FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found.")
        
    if event["organizer_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Only the event organizer can delete this event.")
        
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Event '{event['name']}' has been deleted."}

@app.post("/api/events/{event_id}/attendance")
def mark_participant_attendance(event_id: int, data: AttendanceSchema, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, organizer_id, name FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found.")
        
    if event["organizer_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Only the event organizer can mark attendance.")
        
    new_status = "Attended" if data.attended else "Joined"
    cursor.execute("UPDATE event_participants SET status = ? WHERE event_id = ? AND user_id = ?", (new_status, event_id, data.user_id))
    
    if data.attended:
        award_points(cursor, data.user_id, 20, f"Attended Cleanup Event: {event['name']}")
        send_notification(cursor, data.user_id, "Attendance Verified!", f"You were marked present for '{event['name']}' (+20 points)! Certificate now available.", "badge", f"#event-detail/{event_id}")
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Participant attendance updated to '{new_status}'."}

@app.get("/api/events/{event_id}/certificate/{user_id}")
def get_event_certificate(event_id: int, user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.*, u.full_name as participant_name, u.username, org.full_name as organizer_name, ep.status as participant_status, ep.joined_at
        FROM events e
        JOIN event_participants ep ON e.id = ep.event_id
        JOIN users u ON ep.user_id = u.id
        JOIN users org ON e.organizer_id = org.id
        WHERE e.id = ? AND ep.user_id = ?
    """, (event_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Participant record not found for this event.")
        
    c = dict(row)
    conn.close()
    
    cert_id = f"CERT-ECO-{event_id}-{user_id}-{hex(abs(hash(c['participant_name'])))[-6:].upper()}"
    return {
        "certificate_id": cert_id,
        "participant_name": c["participant_name"],
        "username": c["username"],
        "event_name": c["name"],
        "event_date": c["event_date"],
        "location": c["location_address"],
        "organizer_name": c["organizer_name"],
        "waste_category": c["waste_category"],
        "waste_collected_kg": c["waste_collected_kg"] or 50.0,
        "status": c["status"],
        "participant_status": c["participant_status"],
        "issued_date": c["event_date"]
    }

# --- Notifications Routes ---

@app.get("/api/notifications")
def get_notifications(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (current_user["id"],))
    notifs = [dict(n) for n in cursor.fetchall()]
    conn.close()
    return notifs

@app.post("/api/notifications/read-all")
def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- AI Feature Routes ---

@app.post("/api/ai/classify-waste")
async def ai_classify_waste(file: UploadFile = File(...)):
    """Classifies waste category from image using Pillow CV analysis."""
    contents = await file.read()
    result = classify_waste_image(contents, file.filename)
    return result

@app.post("/api/ai/improve-post")
def ai_improve_post(data: AIPostImproveSchema):
    """Refines post grammar, eco tone, title, and hashtags."""
    return improve_post_with_ai(data.content, data.title)

@app.post("/api/ai/suggest-description")
def ai_suggest_description(data: AISuggestDescSchema):
    """Generates waste report description from category."""
    return suggest_waste_description(data.category, data.location)

@app.post("/api/ai/chat")
def ai_chat_assistant(data: AIChatSchema):
    """Interactive Eco Assistant Chatbot for waste, recycling, and composting advice."""
    return answer_eco_chat(data.query)

@app.post("/api/ai/calculate-impact")
def ai_calculate_impact(data: AIImpactSchema):
    """Calculates carbon footprint and environmental impact metrics per kg of waste."""
    return calculate_environmental_impact(data.waste_kg, data.category)

@app.post("/api/ai/optimize-event")
def ai_optimize_event(data: AIOptimizeEventSchema):
    """Optimizes cleanup event logistics, volunteer headcount, and safety gear."""
    return optimize_cleanup_event(data.location, data.waste_category, data.estimated_area_sqm)

@app.get("/api/ai/cleanliness-index")
def get_cleanliness_index():
    """Computes neighborhood cleanliness index score, grade, hotspots, and green route optimization."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status, severity, location_address FROM waste_reports")
    reports = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return calculate_neighborhood_cleanliness_index(reports)

# --- Global Search Route ---

@app.get("/api/search")
def global_search(query: str):
    if not query or len(query.strip()) < 2:
        return {"posts": [], "events": [], "reports": [], "users": []}
        
    conn = get_db()
    cursor = conn.cursor()
    term = f"%{query}%"
    
    cursor.execute("SELECT p.*, u.username, u.full_name FROM posts p JOIN users u ON p.user_id = u.id WHERE p.title LIKE ? OR p.content LIKE ? LIMIT 10", (term, term))
    posts = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT e.*, u.full_name as organizer_name FROM events e JOIN users u ON e.organizer_id = u.id WHERE e.name LIKE ? OR e.description LIKE ? OR e.location_address LIKE ? LIMIT 10", (term, term, term))
    events = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT r.*, u.username FROM waste_reports r JOIN users u ON r.user_id = u.id WHERE r.title LIKE ? OR r.description LIKE ? OR r.tracking_id LIKE ? LIMIT 10", (term, term, term))
    reports = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT id, username, full_name, profile_pic, points, bio FROM users WHERE username LIKE ? OR full_name LIKE ? LIMIT 10", (term, term))
    users = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "posts": posts,
        "events": events,
        "reports": reports,
        "users": users
    }

# --- Admin Panel Routes ---

@app.get("/api/admin/stats")
def get_admin_stats(admin_user: dict = Depends(get_admin_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cursor.fetchone()["total_users"]
    
    cursor.execute("SELECT COUNT(*) as total_reports FROM waste_reports")
    total_reports = cursor.fetchone()["total_reports"]
    
    cursor.execute("SELECT COUNT(*) as resolved_reports FROM waste_reports WHERE status = 'Resolved'")
    resolved_reports = cursor.fetchone()["resolved_reports"]
    
    cursor.execute("SELECT COUNT(*) as pending_reports FROM waste_reports WHERE status IN ('Reported', 'Under Review', 'Assigned', 'Cleanup in Progress')")
    pending_reports = cursor.fetchone()["pending_reports"]
    
    cursor.execute("SELECT COUNT(*) as total_events FROM events")
    total_events = cursor.fetchone()["total_events"]
    
    cursor.execute("SELECT COUNT(*) as total_participants FROM event_participants")
    total_participants = cursor.fetchone()["total_participants"]
    
    cursor.execute("SELECT COUNT(*) as total_posts FROM posts")
    total_posts = cursor.fetchone()["total_posts"]
    
    cursor.execute("SELECT SUM(waste_collected_kg) as total_waste FROM events WHERE status = 'Completed'")
    total_waste = cursor.fetchone()["total_waste"] or 240.0
    
    # Waste Category Breakdown
    cursor.execute("SELECT category, COUNT(*) as count FROM waste_reports GROUP BY category")
    cat_breakdown = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "total_users": total_users,
        "total_reports": total_reports,
        "resolved_reports": resolved_reports,
        "pending_reports": pending_reports,
        "total_events": total_events,
        "total_participants": total_participants,
        "total_posts": total_posts,
        "total_waste_collected_kg": total_waste,
        "category_breakdown": cat_breakdown
    }

@app.get("/api/admin/users")
def admin_get_users(admin_user: dict = Depends(get_admin_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, points, is_blocked, created_at FROM users ORDER BY created_at DESC")
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return users

@app.post("/api/admin/users/{user_id}/block")
def admin_toggle_block_user(user_id: int, admin_user: dict = Depends(get_admin_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, is_blocked, role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")
    if user["role"] == "admin":
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot block an administrator account.")
        
    new_blocked = 0 if user["is_blocked"] else 1
    cursor.execute("UPDATE users SET is_blocked = ? WHERE id = ?", (new_blocked, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "is_blocked": bool(new_blocked), "message": "User block status updated."}

# --- SPA Public Frontend Routing & Root Fallback ---

@app.get("/")
@app.get("/index")
@app.get("/index.html")
def read_root():
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "EcoTrack API is running!"}

@app.get("/login")
@app.get("/login.html")
def read_login():
    return FileResponse(BASE_DIR / "login.html")

@app.get("/signup")
@app.get("/signup.html")
def read_signup():
    return FileResponse(BASE_DIR / "signup.html")

@app.get("/main")
@app.get("/main.html")
@app.get("/dashboard")
@app.get("/feed")
@app.get("/reports")
@app.get("/events")
@app.get("/map")
@app.get("/leaderboard")
@app.get("/profile")
@app.get("/my-activity")
@app.get("/admin")
@app.get("/post/{post_id}")
@app.get("/event/{event_id}")
def read_main_spa(post_id: Optional[str] = None, event_id: Optional[str] = None):
    return FileResponse(BASE_DIR / "index.html")

@app.get("/style.css")
def read_css():
    return FileResponse(BASE_DIR / "style.css")

@app.get("/frontend/{filename}")
def read_frontend_asset(filename: str):
    file_path = BASE_DIR / "frontend" / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Asset not found.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
