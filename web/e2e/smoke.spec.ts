import { test, expect } from "@playwright/test";

test.describe("AnyStream Web Platform Smoke Test", () => {
  test("loads homepage, renders core elements, and supports navigation", async ({ page }) => {
    // 1. Visit Home Page
    await page.goto("/");
    await expect(page).toHaveTitle(/AnyStream/i);

    // 2. Main title check
    const heading = page.locator("h1");
    await expect(heading).toContainText(/AnyStream Video Downloader/i);

    // 3. Check URL input is visible and interactable
    const urlInput = page.getByRole("textbox");
    await expect(urlInput).toBeVisible();
    await urlInput.fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
    await expect(urlInput).toHaveValue("https://www.youtube.com/watch?v=dQw4w9WgXcQ");

    // 4. Test Language Switcher button
    const langBtn = page.getByTitle(/Switch Language/i);
    await expect(langBtn).toBeVisible();
    await langBtn.click();

    // 5. Navigate to Terms Page
    await page.goto("/terms");
    await expect(page.locator("h1")).toContainText(/Terms of Service|ব্যবহারের নিয়মাবলী/i);

    // 6. Navigate to DMCA Page
    await page.goto("/dmca");
    await expect(page.locator("h1")).toContainText(/DMCA|কপিরাইট/i);
    await expect(page.getByRole("button", { name: /Submit|নোটিশ/i })).toBeVisible();
  });
});

