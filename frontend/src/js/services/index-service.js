import { requestJson } from "./api-client.js";

export class IndexService {
  constructor(api2BaseUrl, getToken) {
    this.api2BaseUrl = api2BaseUrl;
    this._getToken = typeof getToken === "function" ? getToken : () => null;
  }

  _authToken() {
    return this._getToken();
  }

  async listAvailableAssets() {
    const response = await requestJson({
      baseUrl: this.api2BaseUrl,
      path: "/assets/available",
    });
    return response?.assets || [];
  }

  async createIndex({ name, assets }) {
    return requestJson({
      baseUrl: this.api2BaseUrl,
      path: "/indexes",
      method: "POST",
      token: this._authToken(),
      body: {
        name,
        assets,
      },
    });
  }

  async listIndexes() {
    const response = await requestJson({
      baseUrl: this.api2BaseUrl,
      path: "/indexes",
      token: this._authToken(),
    });
    return response?.indexes || [];
  }

  async getIndex(indexId) {
    return requestJson({
      baseUrl: this.api2BaseUrl,
      path: `/indexes/${encodeURIComponent(indexId)}`,
      token: this._authToken(),
    });
  }

  async getIndexPerformance(indexId) {
    return requestJson({
      baseUrl: this.api2BaseUrl,
      path: `/indexes/${encodeURIComponent(indexId)}/performance`,
      token: this._authToken(),
    });
  }

  async updateIndex(indexId, { name, assets }) {
    return requestJson({
      baseUrl: this.api2BaseUrl,
      path: `/indexes/${encodeURIComponent(indexId)}`,
      method: "PUT",
      token: this._authToken(),
      body: {
        name,
        assets,
      },
    });
  }

  async deleteIndex(indexId) {
    return requestJson({
      baseUrl: this.api2BaseUrl,
      path: `/indexes/${encodeURIComponent(indexId)}`,
      method: "DELETE",
      token: this._authToken(),
    });
  }
}
