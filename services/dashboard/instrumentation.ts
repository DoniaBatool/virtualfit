/**
 * Next.js instrumentation — runs before anything else (server-side).
 * Patches broken localStorage injected by Cowork's --localstorage-file flag.
 */
export function register() {
  if (
    typeof globalThis.localStorage === "undefined" ||
    typeof globalThis.localStorage?.getItem !== "function"
  ) {
    const store: Record<string, string> = {};
    // @ts-expect-error patching globalThis in Node.js environment
    globalThis.localStorage = {
      getItem:    (k: string) => store[k] ?? null,
      setItem:    (k: string, v: string) => { store[k] = v; },
      removeItem: (k: string) => { delete store[k]; },
      clear:      () => { Object.keys(store).forEach((k) => delete store[k]); },
      key:        (i: number) => Object.keys(store)[i] ?? null,
      get length() { return Object.keys(store).length; },
    };
  }
}
