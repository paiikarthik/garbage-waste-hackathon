/**
 * EcoTrack Platform Frontend Application Engine
 * Handles SPA Routing, REST API Calls, State Management, Map Rendering,
 * AI Waste Classification, Post Sharing, Cleanup Event Registration, and Admin Panel.
 */

const API_BASE = "";

// Global App State
const state = {
  token: localStorage.getItem("ecotrack_token") || null,
  user: null,
  activeView: "dashboard",
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
  toast.className = `toast ${type === 'error' ? 'bg-red-900' : 'bg-emerald-900'} text-white px-4 py-3 rounded-lg shadow-xl flex items-center gap-3 border border-emerald-700`;
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
    throw new Error(data.detail || data.message || "An unexpected error occurred.");
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
    console.error("Auth failed:", err.message);
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
          <button onclick="openModal('loginModal')" class="px-4 py-2 text-emerald-700 font-semibold hover:bg-emerald-50 rounded-lg">Login</button>
          <button onclick="openModal('signupModal')" class="px-4 py-2 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 shadow-sm">Sign Up</button>
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
  document.querySelectorAll(".view-panel").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-link").forEach(el => el.classList.remove("active"));
  
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
    const posts = await apiFetch(`/api/posts?category=${category}&search=${encodeURIComponent(search)}`);
    state.posts = posts;
    
    const feedContainer = document.getElementById("community-feed-container");
    if (!feedContainer) return;

    if (posts.length === 0) {
      feedContainer.innerHTML = `
        <div class="bg-white p-8 rounded-xl text-center border border-slate-200">
          <span class="material-symbols-outlined text-4xl text-slate-400">forum</span>
          <p class="mt-2 text-slate-600 font-medium">No community posts found.</p>
          <button onclick="openModal('createPostModal')" class="mt-4 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm">Create First Post</button>
        </div>
      `;
      return;
    }

    feedContainer.innerHTML = posts.map(p => `
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-3">
            <img src="${p.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-10 h-10 rounded-full object-cover border border-emerald-500">
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
    loadFeed();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadWasteReports() {
  try {
    const status = document.getElementById("report-status-filter")?.value || "All";
    const category = document.getElementById("report-category-filter")?.value || "All";
    const reports = await apiFetch(`/api/reports?status=${status}&category=${category}`);
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
            <span>Reported by @${r.username}</span>
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
    const events = await apiFetch("/api/events");
    state.events = events;

    const container = document.getElementById("events-grid-container");
    if (!container) return;

    if (events.length === 0) {
      container.innerHTML = `<div class="col-span-full p-8 text-center bg-white rounded-xl border text-slate-500">No cleanup events scheduled. Create one!</div>`;
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
    loadEvents();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function leaveEvent(eventId) {
  try {
    const res = await apiFetch(`/api/events/${eventId}/leave`, { method: "POST" });
    showToast(res.message);
    loadEvents();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Interactive Leaflet Map Engine
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
          <img src="${u.profile_pic || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-12 h-12 rounded-full object-cover border-2 border-emerald-500">
          <div>
            <h4 class="font-bold text-slate-900 text-base cursor-pointer hover:underline" onclick="navigateTo('profile', ${u.id})">${u.full_name}</h4>
            <div class="flex items-center gap-2 mt-1">
              ${u.badges ? u.badges.map(b => `<span title="${b.name}">${b.icon}</span>`).join(' ') : ''}
              <span class="text-xs text-slate-500">@${u.username}</span>
            </div>
          </div>
        </div>

        <div class="text-right">
          <span class="text-2xl font-black text-emerald-700">${u.points}</span>
          <p class="text-xs text-slate-500">Impact Points</p>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(err.message, "error");
  }
}

// --- AI Auto Classification & Post Improvement ---

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

    // Suggest description
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
    showToast("Please enter some post text first to improve with AI.", "error");
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

// --- Modals Engine ---

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

// --- Admin Panel Engine ---

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

// --- Initializer & Event Listeners ---

document.addEventListener("DOMContentLoaded", async () => {
  await checkAuth();
  navigateTo("dashboard");

  // Auth Form Handlers
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("loginEmail").value;
      const pass = document.getElementById("loginPass").value;
      try {
        const res = await apiFetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password: pass })
        });
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem("ecotrack_token", res.token);
        closeModal("loginModal");
        showToast("Logged in successfully!");
        updateUIAuth();
        navigateTo("dashboard");
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = {
        username: document.getElementById("signupUsername").value,
        email: document.getElementById("signupEmail").value,
        password: document.getElementById("signupPass").value,
        full_name: document.getElementById("signupFullName").value,
        location: document.getElementById("signupLocation")?.value || "Mangalore, India",
        bio: document.getElementById("signupBio")?.value || "Environmental advocate"
      };
      try {
        const res = await apiFetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data)
        });
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem("ecotrack_token", res.token);
        closeModal("signupModal");
        showToast("Account created successfully! Welcome to EcoTrack.");
        updateUIAuth();
        navigateTo("dashboard");
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

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
          headers: { "Content-Type": "application/json" },
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
