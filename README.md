# EcoTrack - Smart Waste Management & Community Cleanliness Platform

**EcoTrack** is a production-ready, full-stack Web Application designed to tackle urban garbage disposal issues, organize citizen cleanup drives, foster environmental awareness through a community social feed, track real-time locations with interactive maps, gamify eco-friendly habits with impact points & badges, and leverage AI for waste classification and content assistance.

---
##  Key Features

### 1. User Authentication & Profiles
- Secure user registration, login, logout, forgot password, and reset password flows.
- Hashed passwords using SHA-256 with salts, JWT token authentication, and role authorization (`user` vs `admin`).
- User profile editing: picture, username, location, short bio, points counter, and unlocked eco badges.

### 2. Home Dashboard
- Real-time statistics: Total waste reports, resolved issues, upcoming cleanup events, community impact (kg collected).
- Quick action shortcuts to report waste, organize cleanup drives, or post awareness tips.
- Live recent reports and upcoming events widgets.

### 3.  Waste Reporting System
- Citizen waste report submission: Title, category (Plastic, Food waste, E-waste, Medical waste, Construction, Sewage, Other), severity level (Low, Medium, High, Critical), image upload, location address, and GPS coordinates.
- Automatic unique tracking ID generation (e.g. `REP-89412`).
- Workflow status tracking: `Reported` ➔ `Under Review` ➔ `Assigned` ➔ `Cleanup in Progress` ➔ `Resolved` / `Rejected`.
- Points reward (+10 points) upon reporting waste + bonus (+15 points) when resolved.

### 4.  AI Waste Classifier & Content Tools
- **AI Waste Classification**: Analyzes uploaded waste images via computer vision luminance, texture, and color analysis to predict waste category with confidence score (%) and allow user overrides.
- **AI Post Assistance**: "Improve with AI" button that enhances post grammar, refines environmental awareness tone, generates compelling titles, and suggests relevant hashtags.
- **AI Description Suggestion**: Auto-generates detailed waste problem descriptions based on category and location.

### 5.  Social Feed & Public Share
- Community feed for publishing awareness posts, cleanup updates, and success stories.
- Post likes, comments, and flag/report inappropriate content.
- **Public Share URLs (`/#post/123`)**: Shareable permalinks for WhatsApp, Facebook, X/Twitter, or Web Share API without requiring login to view public post content.

### 6.  Cleanup Event Management
- Create, view, search, and filter cleanup drives.
- Join/Leave cleanup events with capacity caps and participant progress bars.
- Organizer post-event recap submission: Upload before/after photos, actual participant count, estimated waste collected in kg, and waste categories collected.
- Rewards: +50 points for organizing an event, +20 points for joining, +30 points for completing a recap.

### 7.  Interactive Waste Map
- Leaflet JS & OpenStreetMap integration plotting waste reports and cleanup events with custom markers and interactive popups.

### 8. Gamification & Leaderboard
- Contribution Points system tracking all eco actions.
- Badges:
  - **Eco Beginner**: Join the community.
  -  **Waste Reporter**: Submit waste reports.
  -  **Cleanup Volunteer**: Participate in cleanup drives.
  -  **Green Warrior**: Organize community cleanup drives.
  -  **Environmental Champion**: Earn 100+ impact points.
- Community leaderboard ranking top contributors.

### 9.  Real-Time Notifications
- In-app notification bell drawer providing real-time alerts on report status updates, post likes/comments, event registrations, point earnings, and badge unlocks.

### 10.  Admin Dashboard & Moderation
- Platform metrics & chart breakdown.
- Report status management & administrative notes.
- User management table with block/unblock controls.

---

##  Technology Stack

- **Backend**: Python 3.13 + FastAPI + Uvicorn
- **Database**: SQLite (`ecotrack.db`) with relational schemas, foreign keys, and indexes.
- **Authentication**: JWT (JSON Web Tokens) + SHA-256 password hashing.
- **AI Service**: Python PIL (Pillow) Computer Vision feature extraction + NLP text refiner.
- **Frontend**: Single Page Web Application (HTML5, Tailwind CSS, ES6 JavaScript, Google Material Symbols).
- **Maps**: Leaflet JS + OpenStreetMap tiles.
- **Testing**: Pytest + FastAPI TestClient.

---


##  Installation & Execution Guide

### 1. Prerequisites
- Python 3.10+ installed on your system.

### 2. Quick Start Command
Open a terminal in the project directory and run:

```powershell
python backend/main.py
```

The server will initialize the SQLite database `ecotrack.db`, seed sample data & admin credentials, and start listening at:
 **`http://localhost:8000`**

### 3. Admin & Demo Credentials
- **Admin Account**:
  - Email: `admin@ecotrack.org`
  - Password: `admin123`
- **Demo Citizen User**:
  - Email: `karthik@ecotrack.org`
  - Password: `user123`

---
