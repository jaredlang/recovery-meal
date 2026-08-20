import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./api";

vi.mock("./api", async importOriginal => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual,
    getAccount: vi.fn(), getDashboard: vi.fn(), getInventory: vi.fn(), addInventory: vi.fn(), deleteInventory: vi.fn(),
    getRecovery: vi.fn(), getMeals: vi.fn(), getMeal: vi.fn(), generateMeals: vi.fn(), generateImage: vi.fn(), favoriteMeal: vi.fn(), unfavoriteMeal: vi.fn(), selectMeal: vi.fn(),
    getPlan: vi.fn(), createPlannedWorkout: vi.fn(), updatePlannedWorkout: vi.fn(), deletePlannedWorkout: vi.fn(), generatePlannedMeals: vi.fn(), selectPlannedMeal: vi.fn(), getSubstitutions: vi.fn(), replacePlannedIngredient: vi.fn(), checkGroceryLine: vi.fn(),
  };
});

const mocked = vi.mocked(api);
const account = { display_name: "Alex Morgan", email: "alex@example.com", timezone: "UTC", avatar_url: null };
const meal = { id: "meal-1", category: "bowl", name: "Salmon rice bowl", ingredients: [], preparation_steps: ["Cook and serve."], prep_minutes: 20, estimated_calories: 600, protein_g: 35, carbs_g: 70, fat_g: 20, rationale: "Balanced recovery meal", missing_ingredients: [], recovery_match_score: 1, selected: false, selected_at: null, image_status: "ready", image_url: null, favorite: false };

describe("Recovery Meal V2", () => {
  beforeEach(() => {
    vi.clearAllMocks(); history.replaceState({}, "", "/");
    mocked.getAccount.mockResolvedValue(account);
  });

  it("renders the data-driven home dashboard", async () => {
    mocked.getDashboard.mockResolvedValue({ account, latest_workout: null, latest_meal: null, streak: 0, week: { selected: 0, goal: 7, percent: 0, days: [] }, recent_activity: [] });
    render(<App />);
    expect(await screen.findByText(/Good .*Alex/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /recovery meal/i })).toHaveAttribute("href", "/get-meal");
  });

  it("adds pantry items through the shared backend API", async () => {
    history.replaceState({}, "", "/pantry");
    mocked.getInventory.mockResolvedValue([]);
    mocked.addInventory.mockResolvedValue({ id: "item-1", name: "Brown rice", created_at: new Date().toISOString() });
    render(<App />);
    await screen.findByText(/pantry is empty/i);
    fireEvent.change(screen.getByPlaceholderText(/chicken breast/i), { target: { value: "Brown rice" } });
    fireEvent.click(screen.getByRole("button", { name: /add item/i }));
    await waitFor(() => expect(mocked.addInventory).toHaveBeenCalledWith("Brown rice"));
    expect(await screen.findByText("Brown rice")).toBeInTheDocument();
  });

  it("restores meal options from URL-backed workout state", async () => {
    history.replaceState({}, "", "/get-meal/options/workout-1");
    mocked.getRecovery.mockResolvedValue({ workout_id: "workout-1", protein_g: { low: 20, high: 30 }, carbs_g: { low: 40, high: 60 }, fluid_ml: null, calculation_version: "v1" });
    mocked.getMeals.mockResolvedValue({ recommendations: [
      { ...meal, category: "best_recovery_match" },
      { ...meal, id: "meal-2", category: "fastest", name: "Quick yogurt bowl" },
      { ...meal, id: "meal-3", category: "best_use_of_inventory", name: "Pantry omelet" },
    ] });
    render(<App />);
    expect(await screen.findByText("★ Best for recovery")).toBeInTheDocument();
    expect(await screen.findByText("◷ Fastest")).toBeInTheDocument();
    expect(await screen.findByText("▣ Best use of inventory")).toBeInTheDocument();
    expect(screen.getByText("20–30 g")).toBeInTheDocument();
  });

  it("confirms when a meal is selected from its detail page", async () => {
    history.replaceState({}, "", "/meals/meal-1");
    mocked.getMeal.mockResolvedValue(meal);
    mocked.selectMeal.mockResolvedValue({ id: "meal-1", selected: true, selected_at: "2026-08-12T12:00:00Z" });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "I'm making this" }));
    await waitFor(() => expect(mocked.selectMeal).toHaveBeenCalledWith("meal-1"));
    expect(await screen.findByText(/Meal selected\. You're all set to make it\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /I'm making this/i })).toBeDisabled();
  });

  it("summarizes selected planned meals in an accordion and shows pantry-aware groceries", async () => {
    history.replaceState({}, "", "/plan");
    mocked.getPlan.mockResolvedValue({
      starts_on: "2026-08-19", ends_on: "2026-08-25",
      workouts: [{ id: "planned-1", scheduled_for: "2026-08-20", activity_type: "running", display_activity: "Trail running", normalized_activity: "running", duration_minutes: 45, expected_intensity: "high", recovery_target: { protein_g: { low: 20, high: 30 }, carbs_g: { low: 55, high: 70 } }, needs_meal_selection: false, meal_options: [{ id: "planned-meal-1", category: "best_recovery_match", name: "Chicken rice bowl", ingredients: [{ name: "chicken", quantity: 150, unit: "g", available: false }, { name: "rice", quantity: 250, unit: "g", available: true }], preparation_steps: ["Cook and serve."], prep_minutes: 20, estimated_calories: 600, protein_g: 35, carbs_g: 70, fat_g: 20, rationale: "Balanced recovery meal", recovery_match_score: 1, selected: true, selected_at: "2026-08-19T12:00:00Z" }] }],
      grocery_lines: [{ id: "grocery-1", name: "chicken", quantity: 150, unit: "g", category: "Protein", available_at_home: false, checked: false }, { id: "grocery-2", name: "rice", quantity: 250, unit: "g", category: "Grains and Bakery", available_at_home: true, checked: false }],
    });
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Plan your training week" })).toBeInTheDocument();
    expect(screen.getByText(/Trail running · 45 min · High/i)).toBeInTheDocument();
    expect(screen.getByText(/Recovery target: 20-30g protein · 55-70g carbs/i)).toBeInTheDocument();
    expect(screen.getByText(/Selected: Chicken rice bowl · 20 min · 600 kcal/i)).toBeInTheDocument();
    expect(screen.getByText("Protein")).toBeInTheDocument();
    expect(screen.getByText("From 1 selected recovery meal · 2 ingredients")).toBeInTheDocument();
    expect(screen.getByText("Already at home")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Add planned workout" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Collapse week" }));
    expect(screen.getByRole("button", { name: "Expand week" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Next seven days")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "+ Add planned workout" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Expand week" }));
    expect(await screen.findByLabelText("Next seven days")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Add planned workout" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /trail running/i }));
    expect(await screen.findByRole("heading", { name: "Recovery meal" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change meal" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox"));
    await waitFor(() => expect(mocked.checkGroceryLine).toHaveBeenCalledWith("grocery-1", true));
  });
});
