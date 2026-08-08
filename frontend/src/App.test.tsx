import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./api";

vi.mock("./api", () => ({
  getProfile: vi.fn(),
  getInventory: vi.fn(),
  saveProfile: vi.fn(),
  addInventory: vi.fn(),
  deleteInventory: vi.fn(),
  uploadWorkout: vi.fn(),
  correctWorkout: vi.fn(),
  calculateRecovery: vi.fn(),
  generateMeals: vi.fn(),
  selectMeal: vi.fn(),
}));

const mockedApi = vi.mocked(api);

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.getProfile.mockResolvedValue({
      id: "profile-1",
      age: 30,
      sex: "prefer_not_to_say",
      height_cm: 170,
      weight_kg: 70,
      fitness_goal: "maintain_weight",
      foods_to_avoid: [],
      favorite_foods: [],
      max_prep_minutes: 20,
      unit_preference: "metric",
    });
    mockedApi.getInventory.mockResolvedValue([]);
    mockedApi.uploadWorkout.mockResolvedValue({
      id: "workout-1",
      activity_type: "running",
      started_at: null,
      duration_seconds: 1800,
      moving_seconds: 1800,
      distance_meters: 5000,
      elevation_gain_meters: null,
      avg_speed_mps: null,
      avg_heart_rate: null,
      max_heart_rate: null,
      intensity: "moderate",
      met_value: null,
      estimated_calories: { low: 300, high: 400 },
      source_filename: "run.gpx",
    });
    mockedApi.calculateRecovery.mockResolvedValue({
      workout_id: "workout-1",
      protein_g: { low: 20, high: 30 },
      carbs_g: { low: 40, high: 60 },
      fluid_ml: { low: 500, high: 700 },
      calculation_version: "v1",
    });
  });

  it("shows a loading state while generating recommendations", async () => {
    let resolveMeals: ((value: { recommendations: never[] }) => void) | undefined;
    mockedApi.generateMeals.mockImplementation(() => new Promise(resolve => {
      resolveMeals = resolve;
    }));

    const { container } = render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /workout/i }));
    fireEvent.click(screen.getByRole("button", { name: /upload workout/i }));
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: { files: [new File(["gpx"], "run.gpx", { type: "application/gpx+xml" })] },
    });

    expect(screen.getByText(/uploading workout/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/review workout/i)).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/activity/i), { target: { value: "running" } });
    fireEvent.change(screen.getByLabelText(/duration/i), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: /calculate recovery target/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: /generate recommendations/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /generate recommendations/i }));

    expect(screen.getByText(/generating recommendations/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generating recommendations/i })).toBeDisabled();

    resolveMeals?.({ recommendations: [] });
    await waitFor(() => expect(screen.queryByText(/generating recommendations/i)).not.toBeInTheDocument());
  });
});
