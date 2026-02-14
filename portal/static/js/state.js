/**
 * Single-conversation UI state. Used by app.js and api.js.
 */
const state = {
  conversationId: null,
  user: { name: "Stanley Mutisya", role: "Relationship Manager" },
  messages: [],
};

function getState() {
  return state;
}

function setConversationId(id) {
  state.conversationId = id;
}

function setUser(user) {
  state.user = user || state.user;
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
