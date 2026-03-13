import { ROUTE_PATHS } from "../router.js";

export function mountRegisterView(root, { onRegister, onNavigate }) {
  root.innerHTML = `
    <section class="panel">
      <h2 class="page-title">Register</h2>
      <p class="page-subtitle">Create an account to start building custom crypto indexes.</p>
      <div class="stack">
        <div class="alert alert-error" data-feedback hidden></div>
        <form class="stack" data-form>
          <div class="field">
            <label for="register-name">Name (optional)</label>
            <input id="register-name" name="name" type="text" maxlength="100" autocomplete="name">
          </div>
          <div class="field">
            <label for="register-email">Email</label>
            <input id="register-email" name="email" type="email" autocomplete="email" required>
          </div>
          <div class="field">
            <label for="register-password">Password</label>
            <input id="register-password" name="password" type="password" minlength="8" autocomplete="new-password" required>
          </div>
          <div class="field">
            <label for="register-confirm">Confirm Password</label>
            <input id="register-confirm" name="confirm_password" type="password" minlength="8" autocomplete="new-password" required>
          </div>
          <div class="button-row">
            <button class="button button-primary" type="submit" data-submit>Create account</button>
          </div>
        </form>
        <p class="muted">
          Already registered?
          <button type="button" class="inline-link" data-login-link>Go to login</button>
        </p>
      </div>
    </section>
  `;

  const form = root.querySelector("[data-form]");
  const submitButton = root.querySelector("[data-submit]");
  const feedback = root.querySelector("[data-feedback]");

  root.querySelector("[data-login-link]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.login);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.hidden = true;

    const formData = new FormData(form);
    const name = String(formData.get("name") || "").trim();
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");
    const confirmPassword = String(formData.get("confirm_password") || "");

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
    if (password !== confirmPassword) {
      feedback.textContent = "Passwords do not match.";
      feedback.hidden = false;
      return;
    }

    submitButton.disabled = true;
    try {
      await onRegister({ name, email, password });
    } catch (error) {
      feedback.textContent = error instanceof Error ? error.message : "Registration failed.";
      feedback.hidden = false;
    } finally {
      submitButton.disabled = false;
    }
  });
}
