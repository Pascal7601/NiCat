import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.NICAT_E2E_ORIGIN ?? "http://localhost:3000";

export default defineConfig({
    testDir: "./e2e",

    fullyParallel: false,

    // Serialized tests avoid interfering with login throttling
    // or shared pilot examination data.
    workers: 1,

    timeout: 60_000,

    expect: {
        timeout: 10_000,
    },

    reporter: "list",

    use: {
        baseURL,
        trace: "retain-on-failure",
        screenshot: "only-on-failure",
    },

    projects: [
        {
            name: "chromium",
            use: {
                ...devices["Desktop Chrome"],
            },
        },
    ],

    webServer: {
        command: "npm run dev",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        env: {
            ...process.env,
            NEXT_PUBLIC_NICAT_DEMO_MODE: "false",
            NICAT_APP_ORIGIN: baseURL,
        },
    },
});
