import { test, expect } from "@playwright/test";

import AxeBuilder from "@axe-core/playwright";

test("login page meets automated accessibility checks", async ({ page }) => {
    await page.goto("/login");

    const results = await new AxeBuilder({
        page,
    })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();

    const blocking = results.violations.filter(
        (violation) =>
            violation.impact === "critical" || violation.impact === "serious",
    );

    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});

test("login form remains usable on a mobile viewport", async ({ page }) => {
    await page.setViewportSize({
        width: 390,
        height: 844,
    });

    await page.goto("/login");

    await expect(page.getByLabel("Email address")).toBeVisible();

    await expect(page.getByLabel("Password")).toBeVisible();

    await expect(
        page.getByRole("button", {
            name: "Sign in",
        }),
    ).toBeVisible();

    const hasHorizontalOverflow = await page.evaluate(
        () =>
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth,
    );

    expect(hasHorizontalOverflow).toBe(false);
});
