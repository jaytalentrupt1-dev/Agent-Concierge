import assert from "node:assert/strict";
import { readSessionToken, TOKEN_KEY, writeSessionToken } from "./authStorage.js";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    }
  };
}

const localStorage = memoryStorage({ [TOKEN_KEY]: "legacy-local-token" });
const sessionStorage = memoryStorage();

assert.equal(readSessionToken({ localStorage, sessionStorage }), "");
assert.equal(localStorage.getItem(TOKEN_KEY), null);

writeSessionToken("fresh-session-token", { localStorage, sessionStorage });
assert.equal(sessionStorage.getItem(TOKEN_KEY), "fresh-session-token");
assert.equal(localStorage.getItem(TOKEN_KEY), null);
assert.equal(readSessionToken({ localStorage, sessionStorage }), "fresh-session-token");

writeSessionToken("", { localStorage, sessionStorage });
assert.equal(sessionStorage.getItem(TOKEN_KEY), null);
assert.equal(localStorage.getItem(TOKEN_KEY), null);

console.log("auth storage tests passed");
