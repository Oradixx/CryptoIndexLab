import { ROUTE_PATHS } from "../router.js";

export function mountLoginView(root, { onLogin, onNavigate }) {
  root.innerHTML = `
    <section class="panel">
      <h2 class="page-title">Login</h2>
      <p class="page-subtitle">Access your account to create and manage crypto indexes.</p>
      <div class="stack">
        <div class="alert alert-error" data-feedback hidden></div>
        <form class="stack" data-form>
          <div class="field">
            <label for="login-email">Email</label>
            <input id="login-email" name="email" type="email" autocomplete="email" required>
          </div>
          <div class="field">
            <label for="login-password">Password</label>
            <input id="login-password" name="password" type="password" autocomplete="current-password" required>
          </div>
          <div class="button-row">
            <button class="button button-primary" type="submit" data-submit>Login</button>
          </div>
        </form>
        <p class="muted">
          No account yet?
          <button type="button" class="inline-link" data-register-link>Create one now</button>
        </p>
      </div>
    </section>
  `;

  const form = root.querySelector("[data-form]");
  const submitButton = root.querySelector("[data-submit]");
  const feedback = root.querySelector("[data-feedback]");

  root.querySelector("[data-register-link]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.register);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.hidden = true;

    const formData = new FormData(form);
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");

    if (!email || !password) {
      feedback.textContent = "Email and password are required.";
      feedback.hidden = false;
      return;
    }
    if (password.length < 8) {
      feedback.textContent = "Password must contain at least 8 characters.";
      feedback.hidden = false;
      return;
    }

    submitButton.disabled = true;
    try {
      await onLogin({ email, password });
    } catch (error) {
      feedback.textContent = error instanceof Error ? error.message : "Login failed.";
      feedback.hidden = false;
    } finally {
      submitButton.disabled = false;
    }
  });
}
