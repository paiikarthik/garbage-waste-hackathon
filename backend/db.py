import sqlite3
import os
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "ecotrack.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_password(password: str) -> str:
    # Standard secure SHA-256 + salt password hashing
    salt = "ecotrack_salt_2026_clean_green"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            cursor.executescript(f.read())
    conn.commit()

    # Seed Badges
    badges = [
        ('eco_beginner', 'Eco Beginner', 'eco', 'Joined the EcoTrack community and started making a difference', 0),
        ('waste_reporter', 'Waste Reporter', 'delete_sweep', 'Reported waste issues to keep neighborhoods clean', 10),
        ('cleanup_volunteer', 'Cleanup Volunteer', 'cleaning_services', 'Participated in community cleanup drives', 20),
        ('green_warrior', 'Green Warrior', 'public', 'Organized cleanup events and actively led community efforts', 50),
        ('environmental_champion', 'Environmental Champion', 'military_tech', 'Reached 100+ contribution points for outstanding impact', 100),
    ]

    for code, name, icon, desc, pts in badges:
        cursor.execute("""
            INSERT OR IGNORE INTO badges (code, name, icon, description, points_required)
            VALUES (?, ?, ?, ?, ?)
        """, (code, name, icon, desc, pts))
    conn.commit()

    # Seed Admin User if not exists
    cursor.execute("SELECT id FROM users WHERE email = 'admin@ecotrack.org'")
    admin = cursor.fetchone()
    if not admin:
        admin_pass = hash_password("admin123")
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, bio, location, role, points, profile_pic)
            VALUES ('admin', 'admin@ecotrack.org', ?, 'EcoTrack Admin', 'Chief Environmental Officer & Moderator', 'Panambur, Mangalore', 'admin', 500, 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150')
        """, (admin_pass,))
        conn.commit()
        admin_id = cursor.lastrowid
        cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'environmental_champion')", (admin_id,))
        conn.commit()

    # Seed Sample User if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'user'")
    user_count = cursor.fetchone()['cnt']
    if user_count == 0:
        demo_pass = hash_password("user123")
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, bio, location, role, points, profile_pic)
            VALUES ('karthik_eco', 'karthik@ecotrack.org', ?, 'Karthik Pai', 'Passionate about zero-waste living & ocean cleanup', 'Mangalore, India', 'user', 65, 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150')
        """, (demo_pass,))
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'eco_beginner')", (user_id,))
        cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'waste_reporter')", (user_id,))
        cursor.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code) VALUES (?, 'cleanup_volunteer')", (user_id,))
        conn.commit()

        # Seed Sample Waste Reports
        reports = [
            ('REP-89412', user_id, 'Plastic Bottles & Trash near Beach Walkway', 'Huge pile of discarded plastic water bottles and snack wrappers clogging storm drains near the beach entrance.', 'Plastic', 'High', 'Reported', 'https://images.unsplash.com/photo-1621451537084-482c73073a0f?w=600', 'Panambur Beach Road, Mangalore', 12.9141, 74.8560),
            ('REP-44109', user_id, 'Overflowing Organic Waste Bin at Central Market', 'Vegetable waste overflowing into the walkway creating bad odor and attracting flies.', 'Food waste', 'Medium', 'Under Review', 'https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=600', 'Central Market Square, Mangalore', 12.8700, 74.8400),
            ('REP-12903', user_id, 'Discarded E-Waste Monitors on Sidewalk', 'Two CRT monitors and electronic cables dumped improperly by the street curb.', 'E-waste', 'Critical', 'Resolved', 'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=600', 'Kodialbail 3rd Cross, Mangalore', 12.8780, 74.8450)
        ]
        for trk, uid, title, desc, cat, sev, status, img, addr, lat, lng in reports:
            cursor.execute("""
                INSERT INTO waste_reports (tracking_id, user_id, title, description, category, severity, status, image_url, location_address, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (trk, uid, title, desc, cat, sev, status, img, addr, lat, lng))
        conn.commit()

        # Seed Sample Posts
        posts = [
            (user_id, 'Beach Cleanliness Drive Success!', 'We collected over 120 kg of plastic debris during last weekend drive at Panambur Beach! Huge thanks to all 45 volunteers who joined us.', 'Success Stories', 'https://images.unsplash.com/photo-1618477461853-cf6ed80faba5?w=600', 'Panambur Beach', 5, 2),
            (user_id, '5 Simple Ways to Reduce Single-Use Plastic at Home', '1. Carry reusable cotton bags. 2. Refill glass bottles. 3. Avoid plastic straws. 4. Buy bulk grains. 5. Compost food scraps!', 'Awareness', 'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=600', 'Mangalore', 8, 4)
        ]
        for uid, title, content, cat, img, loc, l_cnt, c_cnt in posts:
            cursor.execute("""
                INSERT INTO posts (user_id, title, content, category, image_url, location, likes_count, comments_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, title, content, cat, img, loc, l_cnt, c_cnt))
        conn.commit()

        # Seed Sample Event
        cursor.execute("""
            INSERT INTO events (organizer_id, name, description, cover_image, event_date, start_time, end_time, location_address, latitude, longitude, max_participants, waste_category, required_materials, status)
            VALUES (?, 'Panambur Coastal Cleanup Drive 2026', 'Join us for a massive community beach cleanup! We aim to clear marine plastic waste and restore coastal ecosystem. Gloves and bags will be provided.', 'https://images.unsplash.com/photo-1595278069441-2cf29f8005a4?w=600', '2026-10-15', '07:30 AM', '10:30 AM', 'Panambur Beach Main Entrance, Mangalore', 12.9141, 74.8560, 50, 'Plastic', 'Reusable water bottle, comfortable footwear, sun hat', 'Upcoming')
        """, (user_id,))
        conn.commit()
        event_id = cursor.lastrowid

        cursor.execute("INSERT OR IGNORE INTO event_participants (event_id, user_id) VALUES (?, ?)", (event_id, user_id))
        conn.commit()

        # Seed Sample Notification
        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (?, 'Welcome to EcoTrack! 🌱', 'Thank you for joining EcoTrack! Report waste issues, join cleanup drives, and earn points.', 'badge', '#profile')
        """, (user_id,))
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
