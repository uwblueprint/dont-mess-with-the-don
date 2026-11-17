import axios, { AxiosResponse, AxiosRequestConfig } from "axios";
import { camelizeKeys, decamelizeKeys } from "humps";
import auth from "../firebase";

const baseAPIClient = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL,
});

// Python API uses snake_case, frontend uses camelCase
// convert request and response data to/from snake_case and camelCase through axios interceptors
baseAPIClient.interceptors.response.use((response: AxiosResponse) => {
  if (
    response.data &&
    response.headers["content-type"] === "application/json"
  ) {
    response.data = camelizeKeys(response.data);
  }
  return response;
});

baseAPIClient.interceptors.request.use(async (config: AxiosRequestConfig) => {
  const newConfig = { ...config };

  // getIdToken refreshes the token when it is about to expire
  const token = await auth.currentUser?.getIdToken();
  if (token) {
    newConfig.headers = { ...config.headers, Authorization: `Bearer ${token}` };
  }

  if (config.params) {
    newConfig.params = decamelizeKeys(config.params);
  }
  if (config.data && !(config.data instanceof FormData)) {
    newConfig.data = decamelizeKeys(config.data);
  }

  return newConfig;
});

export default baseAPIClient;
