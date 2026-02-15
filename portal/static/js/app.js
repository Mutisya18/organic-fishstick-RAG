/**
 * Portal UI: profile, dark mode, input, send, welcome cards, message list.
 */

(function () {
  const inputField = document.getElementById("inputField");
  const sendBtn = document.getElementById("sendBtn");
  const messagesContainer = document.getElementById("messagesContainer");
  const welcomeContent = document.getElementById("welcomeContent");
  const quickActions = document.getElementById("quickActions");
  const profileBtn = document.getElementById("profileBtn");
  const profileDropdown = document.getElementById("profileDropdown");
  const darkModeToggle = document.getElementById("darkModeToggle");
  const toggleSwitch = document.getElementById("toggleSwitch");
  const welcomeTitle = document.getElementById("welcomeTitle");
  const welcomeSubtitle = document.getElementById("welcomeSubtitle");
  const headerConversationTitle = document.getElementById("headerConversationTitle");
  const inputWrapper = document.querySelector(".input-wrapper");

  var DEFAULT_PLACEHOLDER = "Ask anything…";
  var WELCOME_PHRASES = [
    "What can I help you with?",
    "What's on your mind today?",
    "How can I assist you?",
    "What would you like to know?",
    "Ask me anything.",
  ];

  let hasStartedChat = false;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function applyUserToUI() {
    const user = getUser();
    if (!user) return;
    const name = user.name || "User";
    const firstName = name.split(" ")[0] || name;
    const initials = name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
    document.getElementById("profileAvatar").textContent = initials;
    document.getElementById("profileName").textContent = name;
    document.getElementById("profileRole").textContent = user.role || "";
    var dropdownName = document.getElementById("dropdownName");
    var dropdownRole = document.getElementById("dropdownRole");
    if (dropdownName) dropdownName.textContent = name;
    if (dropdownRole) dropdownRole.textContent = user.role || "";
    if (welcomeTitle) welcomeTitle.textContent = "Hello, " + firstName;
    if (welcomeSubtitle) {
      var idx = Math.floor(Math.random() * WELCOME_PHRASES.length);
      welcomeSubtitle.textContent = WELCOME_PHRASES[idx];
    }
    if (headerConversationTitle) headerConversationTitle.textContent = "Operations Assistant Chat";
  }

  function addMessage(role, text, meta) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "message " + role;
    if (role === "user") {
      messageDiv.innerHTML = "<div class=\"message-bubble\"><div class=\"message-text\">" + escapeHtml(text) + "</div></div>";
    } else {
      const time = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
      const metaLine = meta ? "<div class=\"message-meta\">" + escapeHtml(meta) + " · " + time + "</div>" : "<div class=\"message-meta\">" + time + "</div>";
      messageDiv.innerHTML = "<div class=\"message-bubble\">" + metaLine + "<div class=\"message-text\">" + escapeHtml(text) + "</div></div>";
    }
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function showTypingIndicator() {
    const typingDiv = document.createElement("div");
    typingDiv.className = "message assistant";
    typingDiv.id = "typingIndicator";
    typingDiv.innerHTML = "<div class=\"typing-indicator\"><div class=\"typing-dot\"></div><div class=\"typing-dot\"></div><div class=\"typing-dot\"></div></div>";
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function hideTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  function hideWelcome() {
    if (welcomeContent) welcomeContent.style.display = "none";
  }

  function showContentLoader() {
    var loader = document.getElementById("contentLoader");
    if (!loader && messagesContainer) {
      loader = document.createElement("div");
      loader.id = "contentLoader";
      loader.className = "content-loader";
      loader.setAttribute("aria-hidden", "true");
      loader.innerHTML =
        '<div class="content-loader-spinner"></div><p class="content-loader-text">Loading…</p>';
      messagesContainer.appendChild(loader);
    }
    if (loader) loader.classList.add("content-loader-visible");
  }

  function hideContentLoader() {
    var loader = document.getElementById("contentLoader");
    if (loader) loader.classList.remove("content-loader-visible");
  }

  function slideOutCards(callback) {
    if (!quickActions) {
      if (callback) callback();
      return;
    }
    const cards = quickActions.querySelectorAll(".action-card");
    cards[0] && cards[0].classList.add("slide-out-1");
    cards[2] && cards[2].classList.add("slide-out-3");
    cards[1] && cards[1].classList.add("slide-out-2");
    setTimeout(callback || (function () {}), 900);
  }

  function showInputError(message) {
    var msg = message || "Invalid input.";
    if (inputWrapper) inputWrapper.classList.add("input-wrapper--error");
    if (inputField) {
      inputField.placeholder = msg;
      inputField.value = ""; /* clear so placeholder is visible */
      inputField.style.height = "auto";
      inputField.classList.remove("scrollable");
      if (sendBtn) sendBtn.disabled = true;
    }
    if (inputWrapper) {
      clearInputError.flashTimer = setTimeout(function () {
        inputWrapper.classList.remove("input-wrapper--error");
        clearInputError.flashTimer = null;
      }, 1200);
    }
  }

  function clearInputError() {
    if (clearInputError.flashTimer) {
      clearTimeout(clearInputError.flashTimer);
      clearInputError.flashTimer = null;
    }
    if (inputWrapper) inputWrapper.classList.remove("input-wrapper--error");
    if (inputField) inputField.placeholder = DEFAULT_PLACEHOLDER;
  }

  function sendMessage(text) {
    const t = (text || (inputField && inputField.value)).trim();
    if (!t) return;

    api.validate(t).then(function (result) {
      if (!result.valid) {
        showInputError(result.message || "Invalid input.");
        return;
      }
      clearInputError();

      function doSend() {
        hideWelcome();
        addMessage("user", t);
        if (inputField) {
          inputField.value = "";
          inputField.style.height = "auto";
          inputField.classList.remove("scrollable");
          sendBtn && (sendBtn.disabled = true);
        }
        showTypingIndicator();
        api.sendMessage(t).then(function (data) {
          hideTypingIndicator();
          const response = (data && data.response) || "No response.";
          const meta = data && data.is_eligibility_flow ? "Eligibility" : "AI Assistant";
          addMessage("assistant", response, meta);
          appendMessage({ role: "user", content: t });
          appendMessage({ role: "assistant", content: response });
          
          // Phase 5: Refresh conversation list after message (updates last_message_at on backend)
          api.listConversations().then(function () {
            renderConversationsList();
          }).catch(function (e) {
            console.warn("Failed to refresh conversation list:", e);
          });
        }).catch(function (err) {
          hideTypingIndicator();
          const msg = (err && err.message) || (err.body && (err.body.detail || JSON.stringify(err.body))) || "Something went wrong.";
          addMessage("assistant", "Error: " + msg, "Error");
        });
      }

      if (!hasStartedChat) {
        hasStartedChat = true;
        slideOutCards(doSend);
      } else {
        doSend();
      }
    });
  }

  // Profile dropdown
  if (profileBtn) {
    profileBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      profileBtn.classList.toggle("active");
      profileDropdown.classList.toggle("show");
    });
  }
  document.addEventListener("click", function () {
    profileBtn && profileBtn.classList.remove("active");
    profileDropdown && profileDropdown.classList.remove("show");
  });
  if (profileDropdown) profileDropdown.addEventListener("click", function (e) { e.stopPropagation(); });

  // Dark mode
  const darkKey = "portal-dark-mode";
  const isDark = localStorage.getItem(darkKey) === "1";
  if (isDark) {
    document.body.classList.add("dark-mode");
    if (toggleSwitch) toggleSwitch.classList.add("active");
  }
  if (darkModeToggle) {
    darkModeToggle.addEventListener("click", function () {
      document.body.classList.toggle("dark-mode");
      toggleSwitch.classList.toggle("active");
      localStorage.setItem(darkKey, document.body.classList.contains("dark-mode") ? "1" : "0");
    });
  }

  // Input: auto-resize, Enter to send, clear validation error on focus/input
  if (inputField) {
    inputField.addEventListener("focus", clearInputError);
    inputField.addEventListener("input", function () {
      clearInputError();
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 160) + "px";
      this.classList.toggle("scrollable", this.scrollHeight > 160);
      sendBtn.disabled = !this.value.trim();
    });
    inputField.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }
  if (sendBtn) sendBtn.addEventListener("click", function () { sendMessage(); });

  // Quick action cards
  if (quickActions) {
    quickActions.addEventListener("click", function (e) {
      const card = e.target.closest(".action-card");
      if (!card) return;
      const prompt = card.getAttribute("data-prompt");
      if (prompt) sendMessage(prompt);
    });
  }

  /**
   * Phase 5: Handle "New Chat" button for multi-conversation
   */
  const newChatBtn = document.getElementById("newChatBtn");
  if (newChatBtn) {
    newChatBtn.addEventListener("click", async function (e) {
      e.preventDefault();
      if (isRequestPending()) {
        console.warn("Create request already pending");
        return;
      }
      
      try {
        newChatBtn.disabled = true;
        showContentLoader();
        var result = await api.createConversation(
          "New Chat",
          getConversationId()
        );
        console.info("New conversation created:", result.conversation.id);

        var listData = await api.listConversations();
        if (listData && listData.conversations) {
          setConversations(listData.conversations);
          setVisibleCount(listData.visible_count || 0);
        }
        renderConversationsList();

        setMessages([]);
        hasStartedChat = false;
        var typingEl = document.getElementById("typingIndicator");
        if (typingEl) typingEl.remove();
        var messageEls = messagesContainer.querySelectorAll(".message");
        for (var i = 0; i < messageEls.length; i++) messageEls[i].remove();
        if (quickActions) {
          quickActions.querySelectorAll(".action-card").forEach(function (card) {
            card.classList.remove("slide-out-1", "slide-out-2", "slide-out-3");
          });
        }
        if (welcomeContent) {
          welcomeContent.style.display = "block";
          if (welcomeSubtitle) {
            var idx = Math.floor(Math.random() * WELCOME_PHRASES.length);
            welcomeSubtitle.textContent = WELCOME_PHRASES[idx];
          }
        }

        if (result.warning && !isWarningShown()) {
          setWarningShown(true);
          showWarningNotification();
        }
        updateConversationBadge();
        if (result.auto_hidden) {
          console.info("Last conversation auto-hidden to maintain limit");
        }
      } catch (e) {
        console.error("Failed to create conversation:", e);
        showInputError("Failed to create conversation");
      } finally {
        newChatBtn.disabled = false;
        hideContentLoader();
      }
    });
  }

  /**
   * Phase 5: Render multi-conversation list in sidebar
   */
  function renderConversationsList() {
    const convs = getConversations();
    const config = getConversationConfig();
    const convList = document.querySelector(".conversations-list");
    if (!convList) return;
    
    // Clear existing items except placeholder
    const items = convList.querySelectorAll(".conversation-item");
    items.forEach(item => item.remove());
    
    // Render each conversation
    convs.forEach(conv => {
      const div = document.createElement("div");
      div.className = "conversation-item";
      if (conv.id === getConversationId()) {
        div.classList.add("active");
      }
      
      // Format last opened time
      const lastOpened = conv.last_opened_at ? new Date(conv.last_opened_at) : null;
      const timeStr = lastOpened 
        ? lastOpened.toLocaleDateString("en-US", { month: "short", day: "numeric" })
        : "Now";
      
      div.innerHTML = `
        <div class="conversation-header">
          <svg class="conversation-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
          <div style="flex: 1; min-width: 0;">
            <div class="conversation-title">${escapeHtml(conv.title || "Chat")}</div>
            <div class="conversation-time">${timeStr}</div>
          </div>
        </div>
      `;
      
      // Handle conversation click
      div.addEventListener("click", async function () {
        try {
          showContentLoader();
          await api.openConversation(conv.id);
          document.querySelectorAll(".conversation-item").forEach(function (item) {
            item.classList.remove("active");
          });
          div.classList.add("active");
          var messages = await api.getMessages(conv.id);
          setMessages(messages);
          hasStartedChat = messages && messages.length > 0;
          if (welcomeContent) {
            welcomeContent.style.display = hasStartedChat ? "none" : "block";
          }
          var typingEl = document.getElementById("typingIndicator");
          if (typingEl) typingEl.remove();
          var messageEls = messagesContainer.querySelectorAll(".message");
          for (var i = 0; i < messageEls.length; i++) messageEls[i].remove();
          if (!hasStartedChat && quickActions) {
            quickActions.querySelectorAll(".action-card").forEach(function (card) {
              card.classList.remove("slide-out-1", "slide-out-2", "slide-out-3");
            });
          }
          if (hasStartedChat) {
            messages.forEach(function (m) {
              addMessage(m.role, m.content, m.role === "assistant" ? "AI Assistant" : null);
            });
          }
        } catch (e) {
          console.error("Failed to switch conversation:", e);
        } finally {
          hideContentLoader();
        }
      });
      
      convList.appendChild(div);
    });
    
    updateConversationBadge();
  }

  /**
   * Phase 5: Show warning notification (exact spec message, dismiss button)
   */
  function showWarningNotification() {
    const message =
      "You have 15 active conversations. At 20, older conversations will be automatically archived.";
    const toast = document.createElement("div");
    toast.className = "warning-toast";
    toast.setAttribute("role", "alert");
    toast.style.cssText =
      "position:fixed;top:20px;right:20px;background:#f59e0b;color:#000;" +
      "padding:12px 16px;border-radius:6px;font-size:14px;z-index:9999;" +
      "box-shadow:0 4px 6px rgba(0,0,0,0.1);max-width:320px;";
    const text = document.createElement("div");
    text.textContent = message;
    text.style.marginBottom = "8px";
    const row = document.createElement("div");
    row.style.display = "flex";
    row.style.justifyContent = "flex-end";
    const dismiss = document.createElement("button");
    dismiss.textContent = "Dismiss";
    dismiss.type = "button";
    dismiss.style.cssText =
      "background:transparent;border:1px solid #000;cursor:pointer;padding:4px 8px;font-size:12px;";
    dismiss.addEventListener("click", function () {
      toast.remove();
    });
    row.appendChild(dismiss);
    toast.appendChild(text);
    toast.appendChild(row);
    document.body.appendChild(toast);
    setTimeout(function () {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 8000);
  }

  /**
   * Phase 5: Update sidebar badge (visibleCount / maxAllowed) with color
   */
  function updateConversationBadge() {
    const badge = document.getElementById("conversationCountBadge");
    if (!badge) return;
    const state = getState();
    const count = state.conversations.visibleCount;
    const max = state.conversations.maxAllowed || 20;
    badge.textContent = "(" + count + "/" + max + ")";
    badge.classList.remove("badge-green", "badge-yellow", "badge-red");
    if (count >= max) {
      badge.classList.add("badge-red");
    } else if (count >= 15) {
      badge.classList.add("badge-yellow");
    } else {
      badge.classList.add("badge-green");
    }
  }


  // Load: init then messages, then render history
  function renderStoredMessages() {
    const messages = getMessages();
    if (!messages || messages.length === 0) return;
    hasStartedChat = true;
    hideWelcome();
    messages.forEach(function (m) {
      addMessage(m.role, m.content, m.role === "assistant" ? "AI Assistant" : null);
    });
  }

  /**
   * Phase 5: Multi-conversation initialization
   * Load list first so sidebar shows all conversations immediately, then config and messages.
   */
  async function initializeMultiConversation() {
    try {
      var convList = await api.listConversations();
      setConversations(convList.conversations || []);
      setVisibleCount(convList.visible_count || 0);
      renderConversationsList();
      updateConversationBadge();
      var config = await api.getConversationConfig();
      if (!config) {
        setConversationConfig(20, 15);
      } else {
        setConversationConfig(config.maxConversations, config.warningThreshold);
      }
      updateConversationBadge();

      if (convList && convList.conversations && convList.conversations.length > 0) {
        var firstConv = convList.conversations[0];
        setConversationId(firstConv.id);
        var messages = await api.getMessages(firstConv.id);
        setMessages(messages);
        renderStoredMessages();
      }
      renderConversationsList();
      updateConversationBadge();
    } catch (e) {
      console.error("Multi-conversation init failed:", e);
      renderConversationsList();
      updateConversationBadge();
    }
  }

  api.init().then(function () {
    applyUserToUI();
    return initializeMultiConversation();
  }).catch(function (err) {
    console.error("Init failed", err);
    applyUserToUI();
  });
})();
