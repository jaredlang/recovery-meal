import { expect, test, type Page, type TestInfo } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const fixture = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "fixtures",
  "workout.gpx",
);

async function captureCheckpoint(page: Page, testInfo: TestInfo, name: string) {
  const screenshotPath = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await testInfo.attach(name, { path: screenshotPath, contentType: "image/png" });
}

test("a new user completes the recovery-meal journey", async ({ page }, testInfo) => {
  const serverErrors: string[] = [];
  page.on("response", response => {
    if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Let's get you set up" })).toBeVisible();
  await page.getByRole("link", { name: "Create profile" }).click();

  await expect(page.getByRole("heading", { name: "Your profile" })).toBeVisible();
  await page.getByLabel("Display name").fill("Jordan Runner");
  await page.getByLabel("Email").fill("jordan@example.test");
  await page.getByLabel("Age").fill("34");
  await page.getByLabel("Sex").selectOption("prefer_not_to_say");
  await page.getByRole("spinbutton", { name: "Height cm" }).fill("175");
  await page.getByRole("spinbutton", { name: "Weight kg" }).fill("70");
  await page.getByLabel("Fitness goal").selectOption("endurance_performance");
  await page.getByLabel("Maximum prep time (minutes)").fill("30");
  await page.getByLabel("Favorite foods").fill("chicken, brown rice, banana");
  await page.getByLabel("Foods to avoid").fill("peanuts");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Your profile is up to date.")).toBeVisible();
  await captureCheckpoint(page, testInfo, "01-profile-saved");

  await page.getByRole("link", { name: "Pantry" }).click();
  await expect(page.getByRole("heading", { name: "What I have" })).toBeVisible();
  const pantryInput = page.getByPlaceholder(/chicken breast, brown rice, apples/i);
  for (const ingredient of ["chicken", "brown rice", "banana"]) {
    await pantryInput.fill(ingredient);
    await page.getByRole("button", { name: "Add item" }).click();
    await expect(page.getByText(ingredient, { exact: true })).toBeVisible();
  }
  await captureCheckpoint(page, testInfo, "02-pantry-populated");

  await page.getByRole("link", { name: "Plan" }).click();
  await expect(page.getByRole("heading", { name: "Plan your training week" })).toBeVisible();
  await page.getByLabel("Activity").fill("Trail running");
  await page.getByLabel("Duration (minutes)").fill("45");
  await page.getByLabel("Expected intensity").selectOption("moderate");
  const createPlannedWorkout = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith("/plan/workouts"),
  );
  await page.getByRole("button", { name: "Add workout" }).click();
  expect((await createPlannedWorkout).ok()).toBe(true);

  await expect(page.getByText(/Trail running · 45 min · Moderate/i)).toBeVisible();
  await expect(page.getByText("Meal not selected")).toBeVisible();
  await page.getByRole("button", { name: /Trail running · 45 min · Moderate/i }).click();
  const generatePlannedMeals = page.waitForResponse(response =>
    response.request().method() === "POST" && /\/plan\/workouts\/[^/]+\/meal-options$/.test(new URL(response.url()).pathname),
  );
  await page.getByRole("button", { name: "Choose recovery meal" }).click();
  expect((await generatePlannedMeals).ok()).toBe(true);
  await expect(page.getByRole("button", { name: /Simple Oat Recovery Bowl/i })).toBeVisible();

  const selectPlannedMeal = page.waitForResponse(response =>
    response.request().method() === "POST" && /\/plan\/meal-options\/[^/]+\/select$/.test(new URL(response.url()).pathname),
  );
  await page.getByRole("button", { name: /Simple Oat Recovery Bowl/i }).click();
  expect((await selectPlannedMeal).ok()).toBe(true);
  await expect(page.getByText(/Selected: Simple Oat Recovery Bowl/i)).toBeVisible();
  await expect(page.getByText("Already at home")).toBeVisible();
  await expect(page.locator(".at-home").getByText(/chicken/i)).toBeVisible();
  await expect(page.getByRole("checkbox")).toHaveCount(2);
  const checkGroceryLine = page.waitForResponse(response =>
    response.request().method() === "PATCH" && /\/plan\/grocery-lines\/[^/]+$/.test(new URL(response.url()).pathname),
  );
  await page.getByRole("checkbox").first().click();
  expect((await checkGroceryLine).ok()).toBe(true);
  await expect(page.getByRole("checkbox").first()).toBeChecked();

  await page.getByRole("button", { name: "Collapse week" }).click();
  await expect(page.getByRole("button", { name: "Expand week" })).toBeVisible();
  await expect(page.getByLabel("Next seven days")).toHaveCount(0);
  await page.getByRole("button", { name: "Expand week" }).click();
  await expect(page.getByLabel("Next seven days")).toBeVisible();
  await captureCheckpoint(page, testInfo, "03-weekly-plan");

  await page.getByRole("link", { name: "Get Meal" }).click();
  await expect(page.getByRole("heading", { name: "Upload your workout" })).toBeVisible();
  await page.locator('input[type="file"][accept*=".gpx"]').setInputFiles(fixture);

  await expect(page.getByRole("heading", { name: "Review your workout" })).toBeVisible();
  await expect(page.getByText("workout.gpx", { exact: true })).toBeVisible();
  await page.getByLabel("Activity").selectOption("running");
  await page.getByLabel("Duration (minutes)").fill("45");
  await page.getByLabel("Pre-workout weight (kg)").fill("70");
  await page.getByLabel("Post-workout weight (kg)").fill("69.5");
  await captureCheckpoint(page, testInfo, "04-workout-review");
  await page.getByRole("button", { name: /Calculate recovery & continue/ }).click();

  await expect(page.getByRole("heading", { name: "Meal options" })).toBeVisible();
  await expect(page.getByText("Protein target")).toBeVisible();
  await expect(page.getByText("Carbohydrate target")).toBeVisible();
  await expect(page.getByText("Hydration")).toBeVisible();
  await page.getByRole("button", { name: "Generate meal options" }).click();

  const selectButtons = page.getByRole("button", { name: "Select meal" });
  await expect(selectButtons).toHaveCount(3);
  const firstMeal = selectButtons.first().locator("xpath=ancestor::article");
  const mealName = (await firstMeal.getByRole("heading", { level: 2 }).textContent())?.trim();
  expect(mealName).toBeTruthy();

  const mealImages = page.getByRole("img");
  await expect(mealImages).toHaveCount(3);
  await expect.poll(async () => mealImages.evaluateAll(images =>
    images.every(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0),
  )).toBe(true);
  await captureCheckpoint(page, testInfo, "05-meal-options");

  const favoriteResponse = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith("/favorite"),
  );
  await firstMeal.getByRole("button", { name: "Toggle favorite" }).click();
  expect((await favoriteResponse).ok()).toBe(true);

  const selectionResponse = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith("/select"),
  );
  await firstMeal.getByRole("button", { name: "Select meal" }).click();
  expect((await selectionResponse).ok()).toBe(true);

  await expect(page).toHaveURL(/\/meals\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: mealName! })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Ingredients/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Preparation/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Nutrition/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /I'm making this/ })).toContainText("✓");
  await expect(page.getByRole("img", { name: mealName! })).toBeVisible();
  await captureCheckpoint(page, testInfo, "06-meal-detail");

  await page.getByRole("link", { name: "Favorites" }).click();
  await expect(page.getByRole("heading", { name: "Favorites" })).toBeVisible();
  await expect(page.getByRole("heading", { name: mealName! })).toBeVisible();
  await expect(page.getByRole("img", { name: mealName! })).toBeVisible();
  await captureCheckpoint(page, testInfo, "07-favorites");

  await page.getByRole("link", { name: "Home" }).click();
  await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening), Jordan!/ })).toBeVisible();
  await expect(page.getByText("Latest workout")).toBeVisible();
  await expect(page.getByText("Your latest recovery meal")).toBeVisible();
  await expect(page.getByRole("heading", { name: mealName! })).toBeVisible();
  await captureCheckpoint(page, testInfo, "08-home-dashboard");

  await page.getByRole("link", { name: "Progress" }).click();
  await expect(page.getByRole("button", { name: "Today" })).toBeVisible();
  await expect(page.getByRole("link", { name: /View workout/ })).toBeVisible();
  await expect(page.getByText(/1-day streak/)).toBeVisible();
  await captureCheckpoint(page, testInfo, "09-progress");
  expect(serverErrors, `Unexpected server responses:\n${serverErrors.join("\n")}`).toEqual([]);
});
