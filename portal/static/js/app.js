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

  function sendMessage(text) {
    const t = (text || (inputField && inputField.value)).trim();
    if (!t) return;

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

  // Input: auto-resize, Enter to send
  if (inputField) {
    inputField.addEventListener("input", function () {
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

  api.init().then(function () {
    applyUserToUI();
    return api.getMessages(getConversationId());
  }).then(function (list) {
    setMessages(list);
    renderStoredMessages();
  }).catch(function (err) {
    console.error("Init failed", err);
    applyUserToUI();
  });
})();
