/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL of the simulation service. Defaults to the `/api` dev-server proxy,
   * which keeps the console same-origin in development and means it cannot ship
   * with a hard-coded backend host.
   */
  readonly VITE_API_BASE?: string;
  /** Value for the `X-API-Key` header. Only needed when the service requires one. */
  readonly VITE_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module '*.json' {
  const value: unknown;
  export default value;
}
