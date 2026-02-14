/**
 * API client: init, get messages, send message (POST /api/chat/send).
 */

const api = {
  async init() {
    const res = await fetch("/api/init", { method: "POST" });
    if (!res.ok) throw new Error("Init failed");
    const data = await res.json();
    setConversationId(data.conversation_id);
    setUser(data.user);
    return data;
  },

  async getMessages(conversationId) {
    const id = conversationId || getConversationId();
    if (!id) return [];
    const res = await fetch(`/api/messages?conversation_id=${encodeURIComponent(id)}`);
    if (!res.ok) return [];
    const data = await res.json();
    setMessages(data);
    return data;
  },

  async validate(content) {
    const res = await fetch("/api/chat/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: content || "" }),
    });
    const data = await res.json();
    return { valid: !!data.valid, message: data.message || null };
  },

  async sendMessage(text) {
    const conversationId = getConversationId();
    const res = await fetch("/api/chat/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text, conversation_id: conversationId || "default" }),
    });
    const data = await res.json();
    if (!res.ok) {
      const err = new Error(data.detail || "Send failed");
      err.status = res.status;
      err.body = data;
      throw err;
    }
    return data;
  },
};
