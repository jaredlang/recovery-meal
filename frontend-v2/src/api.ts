import type { Account, Activity, Dashboard, Favorite, Inventory, Meal, PlannedWorkout, PlannedWorkoutInput, Profile, Progress, Recovery, SubstitutionSuggestion, WeeklyPlan, Workout } from "./types";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
export const MEDIA = API.replace(/\/api\/v1$/, "");

export class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  if (!response.ok) { const body = await response.json().catch(() => null); throw new ApiError(body?.error?.message || `Request failed (${response.status})`, response.status); }
  return response.status === 204 ? undefined as T : response.json();
}
const json = (method: string, body: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const imageUrl = (path: string | null) => path ? (path.startsWith("http") ? path : `${MEDIA}${path}`) : null;
export const getProfile = () => request<Profile>("/profile");
export const saveProfile = (value: Omit<Profile, "id">) => request<Profile>("/profile", json("PUT", value));
export const getAccount = () => request<Account>("/profile/account");
export const saveAccount = (value: Omit<Account, "avatar_url">) => request<Account>("/profile/account", json("PUT", value));
export const uploadAvatar = (file: File) => { const data = new FormData(); data.append("file", file); return request<Account>("/profile/account/avatar", { method: "POST", body: data }); };
export const deleteAccount = () => request<void>("/profile/account", { method: "DELETE" });
export const getInventory = () => request<Inventory[]>("/inventory");
export const addInventory = (name: string) => request<Inventory>("/inventory", json("POST", { name }));
export const deleteInventory = (id: string) => request<void>(`/inventory/${id}`, { method: "DELETE" });
export const uploadWorkout = (file: File) => { const data = new FormData(); data.append("file", file); return request<Workout>("/workouts", { method: "POST", body: data }); };
export const getWorkout = (id: string) => request<Workout>(`/workouts/${id}`);
export const correctWorkout = (id: string, activity_type: Activity, duration_seconds: number) => request<Workout>(`/workouts/${id}/correction`, json("PATCH", { activity_type, duration_seconds }));
export const calculateRecovery = (id: string, pre?: number, post?: number) => request<Recovery>(`/workouts/${id}/recovery-target`, json("POST", { pre_exercise_weight_kg: pre || null, post_exercise_weight_kg: post || null }));
export const getRecovery = (id: string) => request<Recovery>(`/workouts/${id}/recovery-target`);
export const generateMeals = (id: string) => request<{ recommendations: Meal[] }>(`/workouts/${id}/recommendations`, json("POST", {}));
export const getMeals = (id: string) => request<{ recommendations: Meal[] }>(`/workouts/${id}/recommendations`);
export const getMeal = (id: string) => request<Meal>(`/recommendations/${id}`);
export const selectMeal = (id: string) => request<{ id: string; selected: boolean; selected_at: string }>(`/recommendations/${id}/select`, { method: "POST" });
export const generateImage = (id: string) => request<Meal>(`/recommendations/${id}/image`, { method: "POST" });
export const favoriteMeal = (id: string) => request<Favorite>(`/recommendations/${id}/favorite`, { method: "POST" });
export const unfavoriteMeal = (id: string) => request<void>(`/recommendations/${id}/favorite`, { method: "DELETE" });
export const getFavorites = () => request<Favorite[]>("/favorites");
export const getFavorite = (id: string) => request<Favorite>(`/favorites/${id}`);
export const deleteFavorite = (id: string) => request<void>(`/favorites/${id}`, { method: "DELETE" });
export const getDashboard = () => request<Dashboard>("/dashboard");
export const getProgress = (month: string) => request<Progress>(`/progress?month=${month}`);
export const getPlan = () => request<WeeklyPlan>("/plan");
export const createPlannedWorkout = (value: PlannedWorkoutInput) => request<PlannedWorkout>("/plan/workouts", json("POST", value));
export const updatePlannedWorkout = (id: string, value: PlannedWorkoutInput) => request<PlannedWorkout>(`/plan/workouts/${id}`, json("PUT", value));
export const deletePlannedWorkout = (id: string) => request<void>(`/plan/workouts/${id}`, { method: "DELETE" });
export const generatePlannedMeals = (id: string) => request<PlannedWorkout>(`/plan/workouts/${id}/meal-options`, json("POST", {}));
export const selectPlannedMeal = (id: string) => request<WeeklyPlan>(`/plan/meal-options/${id}/select`, { method: "POST" });
export const getSubstitutions = (mealId: string, ingredientName: string) => request<{ ingredient_name: string; suggestions: SubstitutionSuggestion[] }>(`/plan/meal-options/${mealId}/substitutions?ingredient_name=${encodeURIComponent(ingredientName)}`);
export const replacePlannedIngredient = (mealId: string, ingredientName: string, replacementName: string) => request<WeeklyPlan>(`/plan/meal-options/${mealId}/substitutions`, json("POST", { ingredient_name: ingredientName, replacement_name: replacementName }));
export const checkGroceryLine = (id: string, checked: boolean) => request<WeeklyPlan>(`/plan/grocery-lines/${id}`, json("PATCH", { checked }));
