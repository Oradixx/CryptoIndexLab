import { requestJson } from "./api-client.js";

export class IndexService {
  constructor(api2BaseUrl) {
    this.api2BaseUrl = api2BaseUrl;
  }

  async listAvailableAssets() {
    const response = await requestJson({
      baseUrl: this.api2BaseUrl,
      path: "/assets/available",
    });
    return response?.assets || [];
  }

  async createIndex({ name, assets, userId }) {
    return requestJson({
      baseUrl: this.api2BaseUrl,
      path: "/indexes",
      method: "POST",
      body: {
        name,
        assets,
        user_id: userId || null,
      },
    });
  }

  async listIndexes() {
    const response = await requestJson({
      baseUrl: this.api2BaseUrl,
      path: "/indexes",
    });
    return response?.indexes || [];
  }
}
