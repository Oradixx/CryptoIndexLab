import { requestJson } from "./api-client.js";
import { clearStoredToken, getStoredToken, setStoredToken } from "./session.js";

export class AuthService {
  constructor(api1BaseUrl) {
    this.api1BaseUrl = api1BaseUrl;
  }

  getToken() {
    return getStoredToken();
  }

  storeToken(token) {
    setStoredToken(token);
  }

  clearSession() {
    clearStoredToken();
  }

  async register({ email, password, name }) {
    return requestJson({
      baseUrl: this.api1BaseUrl,
      path: "/register",
      method: "POST",
      body: {
        email,
        password,
        name: name || null,
      },
    });
  }

  async login({ email, password }) {
    return requestJson({
      baseUrl: this.api1BaseUrl,
      path: "/login",
      method: "POST",
      body: { email, password },
    });
  }

  async getCurrentUser(token = this.getToken()) {
    if (!token) {
      return null;
    }
    return requestJson({
      baseUrl: this.api1BaseUrl,
      path: "/me",
      token,
    });
  }
}
