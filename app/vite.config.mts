import { resolve } from "path"
import { fileURLToPath } from "url"

import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

const __dirname = fileURLToPath(new URL(".", import.meta.url))

const BACKEND_PORT = 31464

const clientMode = process.env["VITE_CLIENT_MODE"] ?? "node"
const outDir = process.env["VITE_OUT_DIR"] ?? "../dist"

export default defineConfig({
  plugins: [react()],
  root: resolve(__dirname, "frontend"),
  resolve:
    clientMode === "browser"
      ? { alias: { "./client.js": "./client.browser.js" } }
      : {},
  build: {
    outDir,
    emptyOutDir: true,
  },
  server: {
    host: "0.0.0.0",
    port: parseInt(process.env["VITE_PORT"] ?? "3001", 10),
    strictPort: true,
    proxy:
      clientMode === "browser"
        ? undefined
        : {
            "/_rpc": `http://localhost:${BACKEND_PORT}`,
            "/_openapi": `http://localhost:${BACKEND_PORT}`,
          },
  },
})
