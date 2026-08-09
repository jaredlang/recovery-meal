import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./api";

vi.mock("./api", async importOriginal => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual,
    getAccount: vi.fn(), getDashboard: vi.fn(), getInventory: vi.fn(), addInventory: vi.fn(), deleteInventory: vi.fn(),
    getRecovery: vi.fn(), getMeals: vi.fn(), generateMeals: vi.fn(), generateImage: vi.fn(), favoriteMeal: vi.fn(), unfavoriteMeal: vi.fn(), selectMeal: vi.fn(),
  };
});

const mocked = vi.mocked(api);
const account = { display_name: "Alex Morgan", email: "alex@example.com", timezone: "UTC", avatar_url: null };

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
    mocked.getMeals.mockResolvedValue({ recommendations: [] });
    render(<App />);
    expect(await screen.findByText(/Ready for tailored meals/i)).toBeInTheDocument();
    expect(screen.getByText("20–30 g")).toBeInTheDocument();
  });
});
