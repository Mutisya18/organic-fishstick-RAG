/**
 * Login page: form submit, POST /api/auth/login, redirect on success.
 */
(function () {
  const form = document.getElementById("loginForm");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const errorEl = document.getElementById("errorMessage");
  const submitBtn = document.getElementById("submitBtn");

  function setError(msg) {
    if (errorEl) errorEl.textContent = msg || "";
  }

  function setLoading(loading) {
    if (submitBtn) {
      submitBtn.disabled = !!loading;
      submitBtn.textContent = loading ? "Signing in…" : "Sign In";
    }
  }

  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = (emailInput && emailInput.value) ? emailInput.value.trim() : "";
    var password = (passwordInput && passwordInput.value) || "";
    setError("");
    if (!email) {
      setError("Please enter a valid email address");
      return;
    }
    setLoading(true);
    fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email: email, password: password }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) {
            setError(data.error || data.detail || "Unable to connect. Please try again.");
            if (passwordInput) passwordInput.value = "";
            setLoading(false);
            return;
          }
          if (data.success) {
            window.location.href = "/";
            return;
          }
          setError(data.error || "Invalid email or password");
          if (passwordInput) passwordInput.value = "";
          setLoading(false);
        });
      })
      .catch(function () {
        setError("Unable to connect. Please try again.");
        setLoading(false);
      });
  });
})();
