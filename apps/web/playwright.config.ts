import { defineConfig } from "@playwright/test";

// Uses the system Chrome (channel "chrome"); set PW_CHANNEL="" to use Playwright's bundled Chromium.
const channel = process.env.PW_CHANNEL ?? "chrome";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    ...(channel ? { channel } : {}),
    colorScheme: "dark",
  },
  webServer: [
    {
      command:
        "cd ../api && MOCK_LLM=1 MOCK_TTS=1 RATE_LIMIT_ENABLED=0 .venv/bin/uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/api/health",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "VITE_API_URL=http://localhost:8000 npx vite --port 5173",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
