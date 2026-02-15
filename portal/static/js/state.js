/**
 * Multi-conversation UI state manager. Handles conversations, active selection,
 * relevance-based limiting, and warning thresholds.
 *
 * Conversation Limits (from backend config):
 * - maxConversations: Max visible conversations (typically 20)
 * - warningThreshold: Show warning when reached (typically 15)
 * - enabled: Feature flag (true enables multi-conversation)
 */
const state = {
  auth: {
    user: null,
    isAuthenticated: false,
  },
  conversationId: null,
  user: { name: "", role: "" },
  messages: [],

  // Multi-conversation state (Phase 5+)
  conversations: {
    items: [],              // All visible conversations, sorted by relevance
    activeId: null,         // Currently selected conversation ID
    visibleCount: 0,        // Count of non-hidden conversations
    maxAllowed: 20,         // Max allowed from config
    warningThreshold: 15,   // Warning threshold from config
    warningShown: false,    // Session-scoped flag to show warning once
    requestPending: false,  // Prevent rapid-fire requests during creation
  },
};

function getState() {
  return state;
}

function setConversationId(id) {
  state.conversationId = id;
  state.conversations.activeId = id;
}

function setUser(user) {
  if (user) {
    state.user = { name: user.full_name || user.email || "User", role: user.role || "" };
  } else {
    state.user = state.user;
  }
}

function setAuthUser(user) {
  state.auth.user = user || null;
  state.auth.isAuthenticated = !!user;
  if (user) {
    state.user = { name: user.full_name || user.email || "User", role: "" };
  }
}

function clearAuthUser() {
  state.auth.user = null;
  state.auth.isAuthenticated = false;
  state.user = { name: "", role: "" };
}

function isAuthenticated() {
  return state.auth.isAuthenticated;
}

function getCurrentUser() {
  return state.auth.user || null;
}

function setMessages(messages) {
  state.messages = Array.isArray(messages) ? messages : [];
}

function appendMessage(msg) {
  state.messages.push(msg);
}

function getConversationId() {
  return state.conversationId;
}

function getUser() {
  return state.user;
}

function getMessages() {
  return state.messages;
}

/**
 * Multi-conversation state getters
 */
function getConversations() {
  return state.conversations.items;
}

function setConversations(items) {
  state.conversations.items = Array.isArray(items) ? items : [];
}

function setConversationConfig(maxAllowed, warningThreshold) {
  state.conversations.maxAllowed = maxAllowed || 20;
  state.conversations.warningThreshold = warningThreshold || 15;
}

function setVisibleCount(count) {
  state.conversations.visibleCount = count || 0;
}

function setWarningShown(shown) {
  state.conversations.warningShown = !!shown;
}

function isWarningShown() {
  return state.conversations.warningShown;
}

function getConversationConfig() {
  return {
    maxAllowed: state.conversations.maxAllowed,
    warningThreshold: state.conversations.warningThreshold,
  };
}

function setRequestPending(pending) {
  state.conversations.requestPending = !!pending;
}

function isRequestPending() {
  return state.conversations.requestPending;
}
