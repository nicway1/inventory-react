/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
  readonly VITE_ENABLE_DEV_TOOLS: string
  readonly VITE_ENABLE_MOCK_API: string
  readonly VITE_AUTH_COOKIE_NAME: string
  readonly VITE_SESSION_TIMEOUT_MINUTES: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
