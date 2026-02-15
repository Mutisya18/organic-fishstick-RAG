/**
 * API client: init, get messages, send message (POST /api/chat/send).
 * Phase 5 additions: Multi-conversation v2 endpoints and state management.
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

  /**
   * Phase 5: Multi-conversation API v2 endpoints
   */

  async getConversationConfig() {
    try {
      const res = await fetch("/api/v2/config/limits");
      if (!res.ok) return null;
      const data = await res.json();
      setConversationConfig(data.maxConversations, data.warningThreshold);
      return data;
    } catch (e) {
      console.error("Failed to fetch config:", e);
      return null;
    }
  },

  async listConversations() {
    try {
      const res = await fetch("/api/v2/conversations");
      if (!res.ok) return { conversations: [], visibleCount: 0 };
      const data = await res.json();
      setConversations(data.conversations || []);
      setVisibleCount(data.visible_count || 0);
      return data;
    } catch (e) {
      console.error("Failed to list conversations:", e);
      return { conversations: [], visibleCount: 0 };
    }
  },

  async createConversation(title, activeConversationId) {
    try {
      setRequestPending(true);
      const body = {
        title: title || "New Chat",
        active_conversation_id: activeConversationId || null,
      };
      const res = await fetch("/api/v2/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Create failed");
      const data = await res.json();

      setConversationId(data.conversation.id);
      setVisibleCount(data.visible_count);

      if (data.warning && !isWarningShown()) {
        setWarningShown(true);
      }

      (function () {
        const current = getConversations();
        const withNew = [data.conversation].concat(
          current.filter(function (c) {
            return c.id !== data.conversation.id;
          })
        );
        const hiddenId =
          data.auto_hidden && data.auto_hidden.conversation_id
            ? data.auto_hidden.conversation_id
            : null;
        const list = hiddenId
          ? withNew.filter(function (c) {
              return c.id !== hiddenId;
            })
          : withNew;
        setConversations(list);
      })();

      return data;
    } catch (e) {
      console.error("Failed to create conversation:", e);
      throw e;
    } finally {
      setRequestPending(false);
    }
  },

  async openConversation(conversationId) {
    try {
      const res = await fetch(`/api/v2/conversations/${conversationId}/open`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        if (res.status === 404) throw new Error("Conversation not found");
        throw new Error("Mark opened failed");
      }
      const data = await res.json();
      // Updated last_opened_at on backend, update state
      setConversationId(conversationId);
      return data;
    } catch (e) {
      console.error("Failed to mark conversation opened:", e);
      throw e;
    }
  },
};

