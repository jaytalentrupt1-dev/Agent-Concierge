export const TOKEN_KEY = "admin_agent_token";

function browserStorage() {
  if (typeof window === "undefined") {
    return { localStorage: null, sessionStorage: null };
  }
  return {
    localStorage: window.localStorage,
    sessionStorage: window.sessionStorage
  };
}

export function readSessionToken(storage = browserStorage()) {
  const token = storage.sessionStorage?.getItem(TOKEN_KEY) || "";
  storage.localStorage?.removeItem(TOKEN_KEY);
  return token;
}

export function writeSessionToken(token, storage = browserStorage()) {
  const normalizedToken = token || "";
  if (normalizedToken) {
    storage.sessionStorage?.setItem(TOKEN_KEY, normalizedToken);
  } else {
    storage.sessionStorage?.removeItem(TOKEN_KEY);
  }
  storage.localStorage?.removeItem(TOKEN_KEY);
  return normalizedToken;
}
