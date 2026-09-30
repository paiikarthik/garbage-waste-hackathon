/**
 * EcoTrack Platform Frontend Application Engine
 * Handles SPA Routing, REST API Calls, State Management, Leaflet Map Rendering,
 * AI Waste Classification, Post Sharing, Cleanup Event Registration, Profile Views,
 * Activity Logs, Notifications, and Admin Panel.
 */

const API_BASE = "";

// Global App State
const state = {
  token: localStorage.getItem("ecotrack_token") || null,
  user: null,
  activeView: "dashboard",
  activeParam: null,
  reports: [],
  posts: [],
  events: [],
  leaderboard: [],
  notifications: [],
  map: null,
  mapMarkers: [],
  aiClassification: null
};

// Toast Notifications Helper
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container") || createToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast ${type === 'error' ? 'bg-red-900 border-red-700' : 'bg-emerald-900 border-emerald-700'} text-white px-4 py-3 rounded-lg shadow-xl flex items-center gap-3 border`;
  toast.innerHTML = `
    <span class="material-symbols-outlined">${type === 'error' ? 'error' : 'check_circle'}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function createToastContainer() {
  const c = document.createElement("div");
  c.id = "toast-container";
  c.className = "toast-container";
  document.body.appendChild(c);
  return c;
}

// Fetch API Wrapper with Auth Interceptor
async function apiFetch(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) {
      logoutUser();
    }
    throw new Error(data.detail || data.message || "An error occurred.");
  }
  return data;
}

// User Authentication Engine
async function checkAuth() {
  if (!state.token) {
    updateUIAuth();
    return;
  }
  try {
    const user = await apiFetch("/api/auth/me");
    state.user = user;
    updateUIAuth();
  } catch (err) {
    console.error("Auth check failed:", err.message);
    logoutUser();
  }
}

function logoutUser() {
  localStorage.removeItem("ecotrack_token");
  state.token = null;
  state.user = null;
  updateUIAuth();
  showToast("Logged out successfully.", "info");
  navigateTo("dashboard");
}

function updateUIAuth() {
  const authNav = document.getElementById("auth-nav-container");
  const adminNav = document.getElementById("admin-nav-item");
  const notifBtn = document.getElementById("notif-btn");
  const notifBadge = document.getElementById("notif-badge");

  if (state.user) {
    if (authNav) {
      authNav.innerHTML = `
        <div class="relative group flex items-center gap-3">
          <div class="flex items-center gap-2 cursor-pointer" onclick="navigateTo('profile')">
            <img src="${state.user.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-9 h-9 rounded-full border-2 border-emerald-500 object-cover">
            <span class="font-semibold text-slate-800 hidden md:inline">${state.user.full_name}</span>
          </div>
          <button onclick="logoutUser()" class="p-2 text-slate-500 hover:text-red-600 rounded-full hover:bg-slate-100" title="Logout">
            <span class="material-symbols-outlined">logout</span>
          </button>
        </div>
      `;
    }
    if (adminNav) {
      adminNav.style.display = state.user.role === 'admin' ? 'flex' : 'none';
    }
    if (notifBtn) notifBtn.style.display = 'flex';
    if (notifBadge) {
      if (state.user.unread_notifications > 0) {
        notifBadge.innerText = state.user.unread_notifications;
        notifBadge.style.display = 'flex';
      } else {
        notifBadge.style.display = 'none';
      }
    }
  } else {
    if (authNav) {
      authNav.innerHTML = `
        <div class="flex items-center gap-2">
          <a href="login.html" class="px-4 py-2 text-emerald-700 font-semibold hover:bg-emerald-50 rounded-lg">Login</a>
          <a href="signup.html" class="px-4 py-2 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 shadow-sm">Sign Up</a>
        </div>
      `;
    }
    if (adminNav) adminNav.style.display = 'none';
    if (notifBtn) notifBtn.style.display = 'none';
  }
}

// Router & View Loader
function navigateTo(view, param = null) {
  state.activeView = view;
  state.activeParam = param;
  
  // Hide all views
  document.querySelectorAll(".view-panel").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-link").forEach(el => el.classList.remove("active"));
  
  // Highlight sidebar
  const activeLink = document.querySelector(`.nav-link[data-view="${view}"]`);
  if (activeLink) activeLink.classList.add("active");

  const targetView = document.getElementById(`view-${view}`);
  if (targetView) targetView.classList.remove("hidden");

  window.scrollTo(0, 0);

  switch (view) {
    case "dashboard":
      loadDashboard();
      break;
    case "feed":
      loadFeed();
      break;
    case "reports":
      loadWasteReports();
      break;
    case "events":
      loadEvents();
      break;
    case "map":
      initOrUpdateMap();
      break;
    case "leaderboard":
      loadLeaderboard();
      break;
    case "my-activity":
      loadMyActivity();
      break;
    case "profile":
      loadUserProfile(param);
      break;
    case "admin":
      loadAdminDashboard();
      break;
    case "post-detail":
      loadPostDetail(param);
      break;
    case "event-detail":
      loadEventDetail(param);
      break;
    default:
      loadDashboard();
      break;
  }
}

// --- View Renderers ---

async function loadDashboard() {
  try {
    const [reports, events, posts] = await Promise.all([
      apiFetch("/api/reports"),
      apiFetch("/api/events"),
      apiFetch("/api/posts")
    ]);
    state.reports = reports;
    state.events = events;
    state.posts = posts;

    document.getElementById("dash-total-reports").innerText = reports.length;
    document.getElementById("dash-resolved-reports").innerText = reports.filter(r => r.status === 'Resolved').length;
    document.getElementById("dash-upcoming-events").innerText = events.filter(e => e.status === 'Upcoming').length;
    
    // Render Dashboard Lists
    const reportsList = document.getElementById("dash-recent-reports");
    if (reportsList) {
      reportsList.innerHTML = reports.slice(0, 4).map(r => `
        <div class="p-3 bg-slate-50 rounded-lg flex justify-between items-center border border-slate-200">
          <div>
            <h4 class="font-semibold text-slate-800 text-sm">${r.title}</h4>
            <p class="text-xs text-slate-500">${r.location_address}</p>
          </div>
          <span class="badge-status status-${r.status.replace(/\s+/g, '')}">${r.status}</span>
        </div>
      `).join('') || '<p class="text-slate-500 text-sm">No waste reports recorded yet.</p>';
    }

    const eventsList = document.getElementById("dash-recent-events");
    if (eventsList) {
      eventsList.innerHTML = events.slice(0, 3).map(e => `
        <div class="p-3 border border-emerald-100 bg-emerald-50/50 rounded-lg flex justify-between items-center">
          <div>
            <h4 class="font-semibold text-emerald-900 text-sm">${e.name}</h4>
            <p class="text-xs text-emerald-700">📅 ${e.event_date} | 📍 ${e.location_address}</p>
          </div>
          <button onclick="navigateTo('event-detail', ${e.id})" class="px-3 py-1 bg-emerald-600 text-white text-xs font-semibold rounded-md">View</button>
        </div>
      `).join('') || '<p class="text-slate-500 text-sm">No upcoming cleanup events.</p>';
    }
  } catch (err) {
    console.error("Dashboard error:", err);
  }
}

async function loadFeed(category = "All") {
  try {
    const search = document.getElementById("feed-search-input")?.value || "";
    const location = document.getElementById("feed-location-input")?.value || "";
    const posts = await apiFetch(`/api/posts?category=${category}&search=${encodeURIComponent(search)}&location=${encodeURIComponent(location)}`);
    state.posts = posts;
    
    const feedContainer = document.getElementById("community-feed-container");
    if (!feedContainer) return;

    if (posts.length === 0) {
      feedContainer.innerHTML = `
        <div class="bg-white p-8 rounded-xl text-center border border-slate-200">
          <span class="material-symbols-outlined text-4xl text-slate-400">forum</span>
          <p class="mt-2 text-slate-600 font-medium">No community posts found matching your criteria.</p>
          <button onclick="openModal('createPostModal')" class="mt-4 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-bold">Create First Post</button>
        </div>
      `;
      return;
    }

    feedContainer.innerHTML = posts.map(p => `
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-3">
            <img src="${p.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-10 h-10 rounded-full object-cover border border-emerald-500 cursor-pointer" onclick="navigateTo('profile', ${p.user_id})">
            <div>
              <h4 class="font-bold text-slate-900 text-sm cursor-pointer hover:underline" onclick="navigateTo('profile', ${p.user_id})">${p.full_name}</h4>
              <p class="text-xs text-slate-500">@${p.username} • ${new Date(p.created_at).toLocaleDateString()}</p>
            </div>
          </div>
          <span class="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-semibold">${p.category}</span>
        </div>

        <div>
          ${p.title ? `<h3 class="font-bold text-slate-800 text-lg mb-1">${p.title}</h3>` : ''}
          <p class="text-slate-700 whitespace-pre-line text-sm leading-relaxed">${p.content}</p>
        </div>

        ${p.image_url ? `<img src="${p.image_url}" class="w-full max-h-96 object-cover rounded-lg border border-slate-100">` : ''}

        ${p.location ? `<div class="text-xs text-slate-500 flex items-center gap-1"><span class="material-symbols-outlined text-xs">location_on</span>${p.location}</div>` : ''}

        <div class="flex items-center justify-between pt-3 border-t border-slate-100 text-slate-600 text-sm">
          <button onclick="toggleLikePost(${p.id})" class="flex items-center gap-1.5 font-medium hover:text-red-600 transition ${p.is_liked ? 'text-red-600 font-bold' : ''}">
            <span class="material-symbols-outlined text-base">${p.is_liked ? 'favorite' : 'favorite_border'}</span>
            <span>${p.likes_count}</span>
          </button>

          <button onclick="navigateTo('post-detail', ${p.id})" class="flex items-center gap-1.5 font-medium hover:text-emerald-600">
            <span class="material-symbols-outlined text-base">chat_bubble</span>
            <span>${p.comments_count} Comments</span>
          </button>

          <button onclick="openShareModal(${p.id}, '${p.title || 'Community Post'}')" class="flex items-center gap-1.5 font-medium hover:text-emerald-600">
            <span class="material-symbols-outlined text-base">share</span>
            <span>Share</span>
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function toggleLikePost(postId) {
  if (!state.token) {
    showToast("Please login to like posts.", "error");
    openModal("loginModal");
    return;
  }
  try {
    const res = await apiFetch(`/api/posts/${postId}/like`, { method: "POST" });
    if (state.activeView === 'post-detail') {
      loadPostDetail(postId);
    } else {
      loadFeed();
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadWasteReports() {
  try {
    const status = document.getElementById("report-status-filter")?.value || "All";
    const category = document.getElementById("report-category-filter")?.value || "All";
    const location = document.getElementById("report-location-filter")?.value || "";
    const reports = await apiFetch(`/api/reports?status=${status}&category=${category}&location=${encodeURIComponent(location)}`);
    state.reports = reports;

    const list = document.getElementById("waste-reports-list");
    if (!list) return;

    if (reports.length === 0) {
      list.innerHTML = `<div class="p-8 text-center bg-white rounded-xl border text-slate-500">No waste reports match your criteria.</div>`;
      return;
    }

    list.innerHTML = reports.map(r => `
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm flex flex-col md:flex-row">
        <img src="${r.image_url || 'https://images.unsplash.com/photo-1621451537084-482c73073a0f?w=600'}" class="w-full md:w-56 h-48 md:h-auto object-cover">
        <div class="p-5 flex-1 flex flex-col justify-between space-y-3">
          <div>
            <div class="flex justify-between items-start gap-2">
              <div>
                <span class="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">${r.tracking_id}</span>
                <h3 class="font-bold text-slate-900 text-lg mt-1">${r.title}</h3>
              </div>
              <span class="badge-status status-${r.status.replace(/\s+/g, '')}">${r.status}</span>
            </div>
            <p class="text-slate-600 text-sm mt-2 line-clamp-2">${r.description}</p>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 pt-3 border-t text-xs text-slate-500">
            <div class="flex items-center gap-3">
              <span>📁 ${r.category}</span>
              <span>⚠️ Severity: <strong>${r.severity}</strong></span>
              <span>📍 ${r.location_address}</span>
            </div>
            <span class="cursor-pointer hover:underline text-emerald-700 font-semibold" onclick="navigateTo('profile', ${r.user_id})">Reported by @${r.username}</span>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadEvents() {
  try {
    const category = document.getElementById("event-category-filter")?.value || "All";
    const status_filter = document.getElementById("event-status-filter")?.value || "All";
    const location = document.getElementById("event-location-filter")?.value || "";
    const events = await apiFetch(`/api/events?category=${category}&status=${status_filter}&location=${encodeURIComponent(location)}`);
    state.events = events;

    const container = document.getElementById("events-grid-container");
    if (!container) return;

    if (events.length === 0) {
      container.innerHTML = `<div class="col-span-full p-8 text-center bg-white rounded-xl border text-slate-500">No cleanup events match your location criteria.</div>`;
      return;
    }

    container.innerHTML = events.map(e => `
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm flex flex-col justify-between">
        <img src="${e.cover_image || 'https://images.unsplash.com/photo-1595278069441-2cf29f8005a4?w=600'}" class="w-full h-44 object-cover">
        <div class="p-5 space-y-3 flex-1 flex flex-col justify-between">
          <div>
            <div class="flex justify-between items-center text-xs text-emerald-700 font-semibold mb-1">
              <span>📅 ${e.event_date} (${e.start_time} - ${e.end_time})</span>
              <span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">${e.status}</span>
            </div>
            <h3 class="font-bold text-slate-900 text-lg">${e.name}</h3>
            <p class="text-slate-600 text-sm line-clamp-2 mt-1">${e.description}</p>
          </div>

          <div class="space-y-2 pt-2 border-t text-xs text-slate-500">
            <p>📍 ${e.location_address}</p>
            <p>👥 Participants: <strong>${e.participant_count} / ${e.max_participants}</strong></p>
            <div class="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
              <div class="bg-emerald-600 h-full" style="width: ${Math.min(100, (e.participant_count / e.max_participants) * 100)}%"></div>
            </div>
          </div>

          <div class="pt-2 flex gap-2">
            <button onclick="navigateTo('event-detail', ${e.id})" class="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold rounded-lg text-sm text-center">Details</button>
            ${e.is_joined ? `
              <button onclick="leaveEvent(${e.id})" class="px-4 py-2 bg-red-100 text-red-700 hover:bg-red-200 font-semibold rounded-lg text-sm">Leave</button>
            ` : `
              <button onclick="joinEvent(${e.id})" class="px-4 py-2 bg-emerald-600 text-white hover:bg-emerald-700 font-semibold rounded-lg text-sm">Join Event</button>
            `}
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function joinEvent(eventId) {
  if (!state.token) {
    showToast("Please login to join cleanup events.", "error");
    openModal("loginModal");
    return;
  }
  try {
    const res = await apiFetch(`/api/events/${eventId}/join`, { method: "POST" });
    showToast(res.message);
    if (state.activeView === 'event-detail') {
      loadEventDetail(eventId);
    } else {
      loadEvents();
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function leaveEvent(eventId) {
  try {
    const res = await apiFetch(`/api/events/${eventId}/leave`, { method: "POST" });
    showToast(res.message);
    if (state.activeView === 'event-detail') {
      loadEventDetail(eventId);
    } else {
      loadEvents();
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

// User Profile Renderer (Handles Current User & Public Profiles)
async function loadUserProfile(targetUserId = null) {
  const userId = targetUserId || (state.user ? state.user.id : null);
  const container = document.getElementById("user-profile-container");
  if (!container) return;

  if (!userId) {
    container.innerHTML = `
      <div class="bg-white p-8 rounded-xl text-center border text-slate-600">
        <p class="font-medium">Please login to view your user profile.</p>
        <button onclick="openModal('loginModal')" class="mt-4 px-5 py-2 bg-emerald-600 text-white font-bold rounded-lg">Login</button>
      </div>
    `;
    return;
  }

  container.innerHTML = `<div class="p-8 text-center text-slate-500 font-medium">Loading profile details...</div>`;

  try {
    const profile = await apiFetch(`/api/users/${userId}`);
    const isSelf = state.user && state.user.id === profile.id;

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Profile Banner Card -->
        <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-center md:items-start justify-between gap-6">
          <div class="flex flex-col md:flex-row items-center gap-6">
            <img src="${profile.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-24 h-24 rounded-full object-cover border-4 border-emerald-500 shadow-md">
            <div class="text-center md:text-left space-y-1">
              <h2 class="text-2xl font-black text-slate-900">${profile.full_name}</h2>
              <p class="text-sm font-semibold text-slate-500">@${profile.username} • 📍 ${profile.location || 'Mangalore'}</p>
              <p class="text-sm text-slate-700 max-w-lg mt-2">${profile.bio || 'Environmental advocate & eco volunteer.'}</p>
            </div>
          </div>

          <div class="flex flex-col items-center md:items-end gap-3">
            <div class="text-right">
              <span class="text-3xl font-black text-emerald-700">${profile.points}</span>
              <p class="text-xs font-bold text-slate-500 uppercase">Impact Points</p>
            </div>
            ${isSelf ? `
              <button onclick="openModal('editProfileModal')" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-lg text-sm border flex items-center gap-1.5">
                <span class="material-symbols-outlined text-base">edit</span> Edit Profile
              </button>
            ` : ''}
          </div>
        </div>

        <!-- Badges Showcase -->
        <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
          <h3 class="font-bold text-slate-900 text-lg flex items-center gap-2">
            <span>🎖️ Unlocked Eco Badges</span>
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            ${profile.badges && profile.badges.length > 0 ? profile.badges.map(b => `
              <div class="eco-badge-card">
                <div class="badge-shield badge-${b.code}">${b.icon}</div>
                <div>
                  <h4 class="font-bold text-slate-800 text-sm">${b.name}</h4>
                  <p class="text-xs text-slate-500">${b.description}</p>
                </div>
              </div>
            `).join('') : '<p class="text-slate-500 text-sm col-span-full">No badges unlocked yet.</p>'}
          </div>
        </div>

        <!-- Activity Counter Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="bg-white p-4 rounded-xl border text-center shadow-sm">
            <span class="text-2xl font-black text-slate-900">${profile.total_reports}</span>
            <p class="text-xs text-slate-500 font-bold uppercase mt-1">Waste Reports</p>
          </div>
          <div class="bg-white p-4 rounded-xl border text-center shadow-sm">
            <span class="text-2xl font-black text-slate-900">${profile.total_posts}</span>
            <p class="text-xs text-slate-500 font-bold uppercase mt-1">Posts Published</p>
          </div>
          <div class="bg-white p-4 rounded-xl border text-center shadow-sm">
            <span class="text-2xl font-black text-slate-900">${profile.events_joined}</span>
            <p class="text-xs text-slate-500 font-bold uppercase mt-1">Events Joined</p>
          </div>
          <div class="bg-white p-4 rounded-xl border text-center shadow-sm">
            <span class="text-2xl font-black text-slate-900">${profile.events_organized}</span>
            <p class="text-xs text-slate-500 font-bold uppercase mt-1">Events Organized</p>
          </div>
        </div>

        <!-- User Recent Posts -->
        <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 class="font-bold text-slate-900 text-lg">User Activity & Posts</h3>
          <div class="space-y-3">
            ${profile.recent_posts && profile.recent_posts.length > 0 ? profile.recent_posts.map(p => `
              <div class="p-4 bg-slate-50 border rounded-xl flex justify-between items-center">
                <div>
                  <h4 class="font-bold text-slate-800 text-sm">${p.title || 'Community Post'}</h4>
                  <p class="text-xs text-slate-500 line-clamp-1 mt-1">${p.content}</p>
                </div>
                <button onclick="navigateTo('post-detail', ${p.id})" class="px-3 py-1 bg-emerald-600 text-white text-xs font-bold rounded-lg">View</button>
              </div>
            `).join('') : '<p class="text-slate-500 text-sm">No recent posts published.</p>'}
          </div>
        </div>
      </div>
    `;

    // Populate edit modal fields if self
    if (isSelf) {
      document.getElementById("editFullName").value = profile.full_name || "";
      document.getElementById("editBio").value = profile.bio || "";
      document.getElementById("editLocation").value = profile.location || "";
      document.getElementById("editProfilePic").value = profile.profile_pic || "";
    }
  } catch (err) {
    container.innerHTML = `<div class="p-8 bg-white border rounded-xl text-red-600">${err.message}</div>`;
  }
}

// User Activity Log Page
async function loadMyActivity() {
  if (!state.user) {
    showToast("Please login to view your activity log.", "error");
    openModal("loginModal");
    return;
  }
  const container = document.getElementById("my-activity-container");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-slate-500 font-medium">Loading your activity history...</div>`;

  try {
    const [reports, myEvents] = await Promise.all([
      apiFetch(`/api/reports?user_id=${state.user.id}`),
      apiFetch("/api/events/my-events")
    ]);

    container.innerHTML = `
      <div class="space-y-6">
        <!-- My Waste Reports -->
        <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 class="font-bold text-slate-900 text-lg flex items-center gap-2">
            <span class="material-symbols-outlined text-emerald-600">delete_sweep</span> My Submitted Reports
          </h3>
          <div class="space-y-3">
            ${reports.length > 0 ? reports.map(r => `
              <div class="p-4 bg-slate-50 border rounded-xl flex justify-between items-center">
                <div>
                  <span class="text-xs font-mono font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">${r.tracking_id}</span>
                  <h4 class="font-bold text-slate-800 text-sm mt-1">${r.title}</h4>
                  <p class="text-xs text-slate-500">📍 ${r.location_address}</p>
                </div>
                <span class="badge-status status-${r.status.replace(/\s+/g, '')}">${r.status}</span>
              </div>
            `).join('') : '<p class="text-slate-500 text-sm">You haven\'t submitted any waste reports yet.</p>'}
          </div>
        </div>

        <!-- My Organized Events -->
        <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 class="font-bold text-slate-900 text-lg flex items-center gap-2">
            <span class="material-symbols-outlined text-emerald-600">event</span> Events Organized By Me
          </h3>
          <div class="space-y-3">
            ${myEvents.organized.length > 0 ? myEvents.organized.map(e => `
              <div class="p-4 bg-emerald-50/60 border border-emerald-200 rounded-xl flex justify-between items-center">
                <div>
                  <h4 class="font-bold text-slate-900 text-sm">${e.name}</h4>
                  <p class="text-xs text-emerald-800">📅 ${e.event_date} • 👥 ${e.participant_count} Registered</p>
                </div>
                <div class="flex gap-2">
                  <button onclick="navigateTo('event-detail', ${e.id})" class="px-3 py-1 bg-emerald-600 text-white text-xs font-bold rounded-lg">View</button>
                  ${e.status !== 'Completed' ? `
                    <button onclick="openEventRecapModal(${e.id})" class="px-3 py-1 bg-amber-600 text-white text-xs font-bold rounded-lg">Mark Recap</button>
                  ` : ''}
                </div>
              </div>
            `).join('') : '<p class="text-slate-500 text-sm">You haven\'t organized any cleanup events yet.</p>'}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-8 bg-white border rounded-xl text-red-600">${err.message}</div>`;
  }
}

// Single Post Detail Permalink View
async function loadPostDetail(postId) {
  const container = document.getElementById("post-detail-container");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-slate-500 font-medium">Loading post details...</div>`;

  try {
    const post = await apiFetch(`/api/posts/${postId}`);
    container.innerHTML = `
      <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6 max-w-3xl mx-auto">
        <button onclick="navigateTo('feed')" class="text-xs font-bold text-emerald-700 flex items-center gap-1 hover:underline">
          <span class="material-symbols-outlined text-sm">arrow_back</span> Back to Community Feed
        </button>

        <div class="flex justify-between items-center">
          <div class="flex items-center gap-3">
            <img src="${post.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-11 h-11 rounded-full object-cover border border-emerald-500 cursor-pointer" onclick="navigateTo('profile', ${post.user_id})">
            <div>
              <h4 class="font-bold text-slate-900 text-base cursor-pointer hover:underline" onclick="navigateTo('profile', ${post.user_id})">${post.full_name}</h4>
              <p class="text-xs text-slate-500">@${post.username} • ${new Date(post.created_at).toLocaleString()}</p>
            </div>
          </div>
          <span class="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-bold">${post.category}</span>
        </div>

        <div>
          ${post.title ? `<h2 class="font-black text-slate-900 text-2xl mb-2">${post.title}</h2>` : ''}
          <p class="text-slate-700 whitespace-pre-line text-base leading-relaxed">${post.content}</p>
        </div>

        ${post.image_url ? `<img src="${post.image_url}" class="w-full max-h-96 object-cover rounded-xl border">` : ''}

        <div class="flex items-center justify-between pt-4 border-t border-slate-100">
          <button onclick="toggleLikePost(${post.id})" class="flex items-center gap-2 font-bold ${post.is_liked ? 'text-red-600' : 'text-slate-600'}">
            <span class="material-symbols-outlined">${post.is_liked ? 'favorite' : 'favorite_border'}</span>
            <span>${post.likes_count} Likes</span>
          </button>
          <button onclick="openShareModal(${post.id}, '${post.title || 'Community Post'}')" class="flex items-center gap-2 font-bold text-slate-600 hover:text-emerald-600">
            <span class="material-symbols-outlined">share</span> Share
          </button>
        </div>

        <!-- Comments Section -->
        <div class="pt-6 border-t border-slate-200 space-y-4">
          <h3 class="font-bold text-slate-900 text-lg">Comments (${post.comments.length})</h3>

          <div class="flex gap-2">
            <input type="text" id="commentInput-${post.id}" placeholder="Write a comment..." class="flex-1 px-3 py-2 border rounded-lg text-sm outline-none">
            <button onclick="submitComment(${post.id})" class="px-4 py-2 bg-emerald-600 text-white font-bold rounded-lg text-sm">Post</button>
          </div>

          <div class="space-y-3">
            ${post.comments.map(c => `
              <div class="p-3 bg-slate-50 border rounded-xl flex items-start gap-3">
                <img src="${c.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-8 h-8 rounded-full object-cover">
                <div>
                  <div class="flex items-center gap-2">
                    <h5 class="font-bold text-slate-900 text-xs">${c.full_name}</h5>
                    <span class="text-xs text-slate-400">${new Date(c.created_at).toLocaleDateString()}</span>
                  </div>
                  <p class="text-slate-700 text-xs mt-0.5">${c.comment}</p>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-8 bg-white border rounded-xl text-red-600">${err.message}</div>`;
  }
}

async function submitComment(postId) {
  if (!state.token) {
    showToast("Please login to comment.", "error");
    openModal("loginModal");
    return;
  }
  const input = document.getElementById(`commentInput-${postId}`);
  if (!input || !input.value.trim()) return;

  try {
    await apiFetch(`/api/posts/${postId}/comment`, {
      method: "POST",
      body: JSON.stringify({ comment: input.value.trim() })
    });
    input.value = "";
    loadPostDetail(postId);
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Single Event Detail View
async function loadEventDetail(eventId) {
  const container = document.getElementById("event-detail-container");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-slate-500 font-medium">Loading event details...</div>`;

  try {
    const event = await apiFetch(`/api/events/${eventId}`);
    const isOrganizer = state.user && state.user.id === event.organizer_id;

    container.innerHTML = `
      <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6 max-w-4xl mx-auto">
        <button onclick="navigateTo('events')" class="text-xs font-bold text-emerald-700 flex items-center gap-1 hover:underline">
          <span class="material-symbols-outlined text-sm">arrow_back</span> Back to Events List
        </button>

        <div class="flex flex-col md:flex-row gap-6">
          <img src="${event.cover_image || 'https://images.unsplash.com/photo-1595278069441-2cf29f8005a4?w=600'}" class="w-full md:w-80 h-56 object-cover rounded-xl border">
          <div class="space-y-3 flex-1">
            <span class="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-bold">${event.status}</span>
            <h2 class="text-2xl font-black text-slate-900">${event.name}</h2>
            <p class="text-slate-600 text-sm leading-relaxed">${event.description}</p>
            
            <div class="space-y-1 text-xs text-slate-600 border-t pt-3">
              <p>📅 Date & Time: <strong>${event.event_date} (${event.start_time} - ${event.end_time})</strong></p>
              <p>📍 Address: <strong>${event.location_address}</strong></p>
              <p>📁 Waste Category: <strong>${event.waste_category}</strong></p>
              <p>🎒 Required Materials: <strong>${event.required_materials || 'None specified'}</strong></p>
            </div>

            <div class="pt-3 flex gap-3">
              ${event.is_joined ? `
                <button onclick="leaveEvent(${event.id})" class="px-5 py-2.5 bg-red-100 text-red-700 hover:bg-red-200 font-bold rounded-xl text-sm">Leave Event</button>
              ` : `
                <button onclick="joinEvent(${event.id})" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-sm shadow">Join Cleanup Event</button>
              `}
              ${isOrganizer && event.status !== 'Completed' ? `
                <button onclick="openEventRecapModal(${event.id})" class="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-xl text-sm shadow">Submit Event Recap</button>
              ` : ''}
            </div>
          </div>
        </div>

        <!-- Participants List -->
        <div class="border-t pt-6 space-y-4">
          <h3 class="font-bold text-slate-900 text-lg">Registered Participants (${event.participants.length} / ${event.max_participants})</h3>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            ${event.participants.map(p => `
              <div class="p-3 bg-slate-50 border rounded-xl flex items-center gap-3 cursor-pointer" onclick="navigateTo('profile', ${p.id})">
                <img src="${p.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-8 h-8 rounded-full object-cover">
                <div>
                  <h5 class="font-bold text-slate-800 text-xs">${p.full_name}</h5>
                  <span class="text-xs text-slate-500">@${p.username}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-8 bg-white border rounded-xl text-red-600">${err.message}</div>`;
  }
}

// Leaflet Interactive Map Engine
function initOrUpdateMap() {
  const mapContainer = document.getElementById("leaflet-map");
  if (!mapContainer) return;

  if (!state.map) {
    state.map = L.map('leaflet-map').setView([12.9141, 74.8560], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(state.map);
  }

  // Clear existing markers
  state.mapMarkers.forEach(m => state.map.removeLayer(m));
  state.mapMarkers = [];

  // Plot Waste Reports
  state.reports.forEach(r => {
    if (r.latitude && r.longitude) {
      const marker = L.marker([r.latitude, r.longitude]).addTo(state.map);
      marker.bindPopup(`
        <div class="p-2 space-y-1">
          <span class="font-mono text-xs text-emerald-700 font-bold">${r.tracking_id}</span>
          <h4 class="font-bold text-sm">${r.title}</h4>
          <p class="text-xs text-slate-600">${r.location_address}</p>
          <p class="text-xs">Category: ${r.category} | Severity: <strong>${r.severity}</strong></p>
        </div>
      `);
      state.mapMarkers.push(marker);
    }
  });

  // Plot Cleanup Events
  state.events.forEach(e => {
    if (e.latitude && e.longitude) {
      const marker = L.marker([e.latitude, e.longitude]).addTo(state.map);
      marker.bindPopup(`
        <div class="p-2 space-y-1">
          <span class="font-mono text-xs text-purple-700 font-bold">EVENT</span>
          <h4 class="font-bold text-sm">${e.name}</h4>
          <p class="text-xs text-slate-600">📍 ${e.location_address}</p>
          <p class="text-xs">📅 ${e.event_date} (${e.start_time})</p>
        </div>
      `);
      state.mapMarkers.push(marker);
    }
  });
}

async function filterMapByLocation() {
  const loc = document.getElementById("map-location-input")?.value || "";
  try {
    const [reports, events] = await Promise.all([
      apiFetch(`/api/reports?location=${encodeURIComponent(loc)}`),
      apiFetch(`/api/events?location=${encodeURIComponent(loc)}`)
    ]);
    state.reports = reports;
    state.events = events;
    initOrUpdateMap();
    if (reports.length > 0 && reports[0].latitude && reports[0].longitude) {
      state.map.setView([reports[0].latitude, reports[0].longitude], 13);
    } else if (events.length > 0 && events[0].latitude && events[0].longitude) {
      state.map.setView([events[0].latitude, events[0].longitude], 13);
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadLeaderboard() {
  try {
    const leaderboard = await apiFetch("/api/users/leaderboard");
    state.leaderboard = leaderboard;

    const list = document.getElementById("leaderboard-list");
    if (!list) return;

    list.innerHTML = leaderboard.map((u, index) => `
      <div class="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between shadow-sm">
        <div class="flex items-center gap-4">
          <span class="font-black text-lg ${index === 0 ? 'text-amber-500' : index === 1 ? 'text-slate-400' : index === 2 ? 'text-amber-700' : 'text-slate-500'} w-6">#${index + 1}</span>
          <img src="${u.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-12 h-12 rounded-full object-cover border-2 border-emerald-500 cursor-pointer" onclick="navigateTo('profile', ${u.id})">
          <div>
            <h4 class="font-bold text-slate-900 text-base cursor-pointer hover:underline" onclick="navigateTo('profile', ${u.id})">${u.full_name}</h4>
            <div class="flex items-center gap-1.5 mt-1">
              ${u.badges ? u.badges.map(b => `<span class="badge-shield badge-${b.code} !w-6 !h-6 !text-xs !rounded-md" title="${b.name}">${b.icon}</span>`).join('') : ''}
              <span class="text-xs text-slate-500">@${u.username}</span>
            </div>
          </div>
        </div>

        <div class="text-right">
          <span class="text-2xl font-black text-emerald-700">${u.points}</span>
          <p class="text-xs text-slate-500 font-bold uppercase">Impact Points</p>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

// AI Auto Classification & Post Improvement
async function triggerAIWasteClassification(input) {
  const file = input.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  const statusEl = document.getElementById("ai-classify-status");
  if (statusEl) statusEl.innerHTML = `<span class="text-emerald-700 font-semibold animate-pulse">🤖 AI analyzing waste image...</span>`;

  try {
    const res = await apiFetch("/api/ai/classify-waste", {
      method: "POST",
      body: formData
    });
    state.aiClassification = res;
    if (statusEl) {
      statusEl.innerHTML = `
        <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex justify-between items-center text-xs text-emerald-900">
          <div>
            <strong>AI Prediction:</strong> <span class="font-bold text-sm text-emerald-700">${res.category}</span>
            <span class="ml-2 bg-emerald-200 text-emerald-800 px-2 py-0.5 rounded font-mono">${res.confidence}% Confidence</span>
          </div>
          <span class="text-slate-500">You can override below</span>
        </div>
      `;
    }
    const catSelect = document.getElementById("reportCategory");
    if (catSelect) catSelect.value = res.category;

    const descRes = await apiFetch("/api/ai/suggest-description", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: res.category })
    });
    const descInput = document.getElementById("reportDescription");
    if (descInput && !descInput.value) {
      descInput.value = descRes.description;
    }
  } catch (err) {
    if (statusEl) statusEl.innerHTML = `<span class="text-red-600 text-xs">AI analysis failed. Please select category manually.</span>`;
  }
}

async function improvePostWithAI() {
  const textInput = document.getElementById("postText");
  const titleInput = document.getElementById("postTitle");
  if (!textInput || !textInput.value) {
    showToast("Please enter post text first.", "error");
    return;
  }

  showToast("Enhancing post with AI NLP...", "info");
  try {
    const res = await apiFetch("/api/ai/improve-post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: textInput.value, title: titleInput ? titleInput.value : "" })
    });

    textInput.value = res.full_text;
    if (titleInput) titleInput.value = res.title;
    showToast("Post enhanced successfully with AI!");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Modal Handlers
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("open");
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("open");
}

function openShareModal(postId, title) {
  const permalink = `${window.location.origin}/#post/${postId}`;
  const modal = document.getElementById("shareModal");
  const input = document.getElementById("shareLinkInput");
  if (input) input.value = permalink;

  const waBtn = document.getElementById("shareWhatsApp");
  if (waBtn) waBtn.href = `https://api.whatsapp.com/send?text=${encodeURIComponent(`Check out this post on EcoTrack: ${title} ${permalink}`)}`;

  const fbBtn = document.getElementById("shareFacebook");
  if (fbBtn) fbBtn.href = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(permalink)}`;

  const twBtn = document.getElementById("shareTwitter");
  if (twBtn) twBtn.href = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(permalink)}`;

  openModal("shareModal");
}

function copyShareLink() {
  const input = document.getElementById("shareLinkInput");
  if (input) {
    input.select();
    navigator.clipboard.writeText(input.value);
    showToast("Link copied to clipboard!");
  }
}

function openEventRecapModal(eventId) {
  state.recapEventId = eventId;
  openModal("eventRecapModal");
}

// Admin Panel
async function loadAdminDashboard() {
  if (!state.user || state.user.role !== 'admin') {
    showToast("Access Denied: Admin authorization required.", "error");
    navigateTo("dashboard");
    return;
  }
  try {
    const [stats, users] = await Promise.all([
      apiFetch("/api/admin/stats"),
      apiFetch("/api/admin/users")
    ]);

    document.getElementById("admin-total-users").innerText = stats.total_users;
    document.getElementById("admin-total-reports").innerText = stats.total_reports;
    document.getElementById("admin-resolved-reports").innerText = stats.resolved_reports;
    document.getElementById("admin-waste-collected").innerText = `${stats.total_waste_collected_kg} kg`;

    const userTable = document.getElementById("admin-users-table");
    if (userTable) {
      userTable.innerHTML = users.map(u => `
        <tr class="border-b">
          <td class="p-3 text-sm flex items-center gap-2">
            <img src="${u.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-7 h-7 rounded-full">
            <div>
              <p class="font-bold text-slate-800">${u.full_name}</p>
              <p class="text-xs text-slate-500">@${u.username}</p>
            </div>
          </td>
          <td class="p-3 text-sm">${u.email}</td>
          <td class="p-3 text-sm"><span class="px-2 py-0.5 text-xs font-bold rounded ${u.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-700'}">${u.role}</span></td>
          <td class="p-3 text-sm font-mono font-bold text-emerald-700">${u.points} pts</td>
          <td class="p-3 text-sm">
            ${u.role !== 'admin' ? `
              <button onclick="toggleBlockUser(${u.id})" class="px-3 py-1 ${u.is_blocked ? 'bg-emerald-600 text-white' : 'bg-red-100 text-red-700'} text-xs font-semibold rounded">
                ${u.is_blocked ? 'Unblock' : 'Block'}
              </button>
            ` : '-'}
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function toggleBlockUser(userId) {
  try {
    const res = await apiFetch(`/api/admin/users/${userId}/block`, { method: "POST" });
    showToast(res.message);
    loadAdminDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Notifications Renderer
async function loadNotifications() {
  if (!state.token) return;
  try {
    const notifications = await apiFetch("/api/notifications");
    state.notifications = notifications;

    const list = document.getElementById("notifications-list");
    if (!list) return;

    if (notifications.length === 0) {
      list.innerHTML = `<p class="p-4 text-center text-slate-500 text-sm">No notifications yet.</p>`;
      return;
    }

    list.innerHTML = notifications.map(n => `
      <div class="p-3 border-b hover:bg-slate-50 flex justify-between items-center ${n.is_read ? 'opacity-60' : 'bg-emerald-50/40'}">
        <div>
          <h4 class="font-bold text-slate-800 text-sm">${n.title}</h4>
          <p class="text-xs text-slate-600 mt-0.5">${n.message}</p>
          <span class="text-xs text-slate-400">${new Date(n.created_at).toLocaleString()}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error("Notifications error:", err);
  }
}

async function markNotificationsRead() {
  try {
    await apiFetch("/api/notifications/read-all", { method: "POST" });
    if (state.user) state.user.unread_notifications = 0;
    updateUIAuth();
    loadNotifications();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Hash Routing Handler
function handleHashRoute() {
  const hash = window.location.hash.replace("#", "");
  if (!hash) {
    navigateTo("dashboard");
    return;
  }

  const parts = hash.split("/");
  const route = parts[0];
  const param = parts[1] ? parseInt(parts[1], 10) || parts[1] : null;

  navigateTo(route, param);
}

// Submissions Engine
async function submitPost() {
  if (!state.token) {
    showToast("Please login to create posts.", "error");
    openModal("loginModal");
    return;
  }
  const content = document.getElementById("postText").value;
  const title = document.getElementById("postTitle")?.value || "";
  if (!content.trim()) {
    showToast("Please write some post content.", "error");
    return;
  }

  try {
    const res = await apiFetch("/api/posts", {
      method: "POST",
      body: JSON.stringify({ title, content, category: "Awareness" })
    });
    closeModal("createPostModal");
    document.getElementById("postText").value = "";
    showToast("Post published successfully! (+5 pts)");
    navigateTo("feed");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitEvent(e) {
  if (e) e.preventDefault();
  if (!state.token) {
    showToast("Please login to create cleanup events.", "error");
    openModal("loginModal");
    return;
  }

  const payload = {
    name: document.getElementById("eventName").value,
    description: document.getElementById("eventDesc").value,
    event_date: document.getElementById("eventDate").value,
    start_time: document.getElementById("eventStartTime").value,
    end_time: document.getElementById("eventEndTime").value,
    location_address: document.getElementById("eventAddress").value,
    max_participants: parseInt(document.getElementById("eventMaxPart").value, 10) || 50,
    waste_category: document.getElementById("eventWasteCat").value,
    required_materials: document.getElementById("eventMaterials").value
  };

  try {
    const res = await apiFetch("/api/events", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    closeModal("createEventModal");
    showToast("Cleanup event published successfully! (+50 pts)");
    navigateTo("events");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitEventRecap(e) {
  if (e) e.preventDefault();
  if (!state.recapEventId) return;

  const payload = {
    actual_participants: parseInt(document.getElementById("recapParticipants").value, 10) || 0,
    waste_collected_kg: parseFloat(document.getElementById("recapWasteKg").value) || 0,
    waste_types_collected: document.getElementById("recapWasteTypes").value || "Mixed"
  };

  try {
    await apiFetch(`/api/events/${state.recapEventId}/recap`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    closeModal("eventRecapModal");
    showToast("Event recap submitted! (+30 bonus pts)");
    navigateTo("event-detail", state.recapEventId);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitProfileUpdate(e) {
  if (e) e.preventDefault();
  const payload = {
    full_name: document.getElementById("editFullName").value,
    bio: document.getElementById("editBio").value,
    location: document.getElementById("editLocation").value,
    profile_pic: document.getElementById("editProfilePic").value
  };

  try {
    const res = await apiFetch("/api/users/profile", {
      method: "PUT",
      body: JSON.stringify(payload)
    });
    closeModal("editProfileModal");
    showToast("Profile updated successfully!");
    state.user = { ...state.user, ...res.user };
    updateUIAuth();
    loadUserProfile();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Initializer & Event Listeners
document.addEventListener("DOMContentLoaded", async () => {
  await checkAuth();

  // Route URL hash
  window.addEventListener("hashchange", handleHashRoute);
  handleHashRoute();

  // Create Event Form
  const eventForm = document.getElementById("createEventForm");
  if (eventForm) eventForm.addEventListener("submit", submitEvent);

  // Event Recap Form
  const recapForm = document.getElementById("eventRecapForm");
  if (recapForm) recapForm.addEventListener("submit", submitEventRecap);

  // Edit Profile Form
  const profileForm = document.getElementById("editProfileForm");
  if (profileForm) profileForm.addEventListener("submit", submitProfileUpdate);

  // Waste Report Form Submit
  const reportForm = document.getElementById("createReportForm");
  if (reportForm) {
    reportForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.token) {
        showToast("Please login to report waste issues.", "error");
        openModal("loginModal");
        return;
      }
      
      const fileInput = document.getElementById("reportImageFile");
      let imageUrl = null;

      if (fileInput && fileInput.files[0]) {
        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        const uploadRes = await apiFetch("/api/upload", { method: "POST", body: formData });
        imageUrl = uploadRes.url;
      }

      const payload = {
        title: document.getElementById("reportTitle").value,
        description: document.getElementById("reportDescription").value,
        category: document.getElementById("reportCategory").value,
        severity: document.getElementById("reportSeverity").value,
        location_address: document.getElementById("reportAddress").value,
        image_url: imageUrl
      };

      try {
        const res = await apiFetch("/api/reports", {
          method: "POST",
          body: JSON.stringify(payload)
        });
        closeModal("createReportModal");
        showToast(`Waste report ${res.tracking_id} submitted successfully! (+10 pts)`);
        navigateTo("reports");
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
});
