import { randomUUID } from "node:crypto";

import { test, expect } from "@playwright/test";

test("student can complete a real examination workflow", async ({ page }) => {
    test.skip(
        process.env.NICAT_E2E_DATABASE_ISOLATED !== "yes",
        "Requires an isolated disposable E2E database.",
    );

    const email = `e2e-${randomUUID()}@example.test`;

    const password = "NiCat-E2E-StrongPassword!2026";

    // 1. Register a test student.
    await page.goto("/register");

    await page.getByLabel("Email address").fill(email);

    await page
        .getByLabel("Password", {
            exact: true,
        })
        .fill(password);

    await page.getByLabel("Confirm password").fill(password);

    await page
        .getByRole("button", {
            name: "Create account",
        })
        .click();

    await expect(page).toHaveURL(/\/login\/?(?:\?.*)?$/);

    // 2. Login with the newly created account.
    await page.getByLabel("Email address").fill(email);

    await page.getByLabel("Password").fill(password);

    await page
        .getByRole("button", {
            name: "Sign in",
        })
        .click();

    await expect(page).toHaveURL(/\/dashboard\/?$/);

    // 3. Confirm that JWT cookies are HttpOnly.
    const cookies = await page.context().cookies();

    const accessCookie = cookies.find((cookie) => cookie.name === "nicat_at");

    expect(accessCookie).toBeDefined();
    expect(accessCookie?.httpOnly).toBe(true);
    expect(accessCookie?.path).toBe("/api");

    // 4. Open a published examination.
    await page.goto("/exams");

    await page
        .getByRole("link", {
            name: /view exam/i,
        })
        .first()
        .click();

    await expect(
        page.getByRole("button", {
            name: /start examination/i,
        }),
    ).toBeVisible();

    await page
        .getByRole("button", {
            name: /start examination/i,
        })
        .click();

    await expect(page).toHaveURL(/\/attempts\/[0-9a-f-]+/);

    // The pilot datasets begin with a single-choice question.
    const firstRadio = page.getByRole("radio").first();

    await expect(firstRadio).toBeVisible();

    // 5. Save an answer and verify the backend response.
    const saveResponse = page.waitForResponse(
        (response) =>
            response.url().includes("/responses/") &&
            response.request().method() === "PUT",
    );

    await firstRadio.check();

    expect((await saveResponse).status()).toBe(200);

    // 6. Reload: the answer must still be saved in PostgreSQL.
    await page.reload();

    await expect(page.getByRole("radio").first()).toBeChecked();

    // 7. Submit the examination.
    page.once("dialog", (dialog) => {
        void dialog.accept();
    });

    await page
        .getByRole("button", {
            name: /submit examination/i,
        })
        .click();

    await expect(page).toHaveURL(/\/results\/[0-9a-f-]+/);

    // 8. Verify the results interface loaded.
    await expect(
        page.getByRole("heading", {
            name: /your examination result/i,
        }),
    ).toBeVisible();

    await expect(
        page.getByText(/review in progress|finalized result/i),
    ).toBeVisible();
});
