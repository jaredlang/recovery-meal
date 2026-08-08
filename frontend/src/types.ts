export type Activity = "walking" | "hiking" | "running" | "cycling" | "unknown";
export type Profile = { id: string; age: number; sex: string; height_cm: number; weight_kg: number; fitness_goal: string; foods_to_avoid: string[]; favorite_foods: string[]; max_prep_minutes: number | null; unit_preference: "metric" | "imperial" };
export type Inventory = { id: string; name: string; created_at: string };
export type Workout = { id: string; activity_type: Activity | string; started_at: string | null; duration_seconds: number | null; moving_seconds: number | null; distance_meters: number | null; elevation_gain_meters: number | null; avg_speed_mps: number | null; avg_heart_rate: number | null; max_heart_rate: number | null; intensity: string | null; met_value: number | null; estimated_calories: { low: number; high: number } | null; source_filename: string };
export type Recovery = { workout_id: string; protein_g: { low: number; high: number }; carbs_g: { low: number; high: number }; fluid_ml: { low: number; high: number } | null; calculation_version: string };
export type Ingredient = { name: string; quantity: number; unit: string; available: boolean };
export type Meal = { id: string; category: string; name: string; ingredients: Ingredient[]; preparation_steps: string[]; prep_minutes: number; estimated_calories: number; protein_g: number; carbs_g: number; fat_g: number; rationale: string; missing_ingredients: string[]; recovery_match_score: number; selected: boolean };

