import type { Inventory, Meal, Profile, Recovery, Workout, Activity } from "./types";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error?.message || `Request failed (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export const getProfile = () => request<Profile>("/profile");
export const saveProfile = (profile: Omit<Profile, "id">) => request<Profile>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile) });
export const getInventory = () => request<Inventory[]>("/inventory");
export const addInventory = (name: string) => request<Inventory>("/inventory", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
export const deleteInventory = (id: string) => request<void>(`/inventory/${id}`, { method: "DELETE" });
export const uploadWorkout = (file: File) => { const data = new FormData(); data.append("file", file); return request<Workout>("/workouts", { method: "POST", body: data }); };
export const correctWorkout = (id: string, activity_type: Activity, duration_seconds: number) => request<Workout>(`/workouts/${id}/correction`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ activity_type, duration_seconds }) });
export const calculateRecovery = (id: string, pre?: number, post?: number) => request<Recovery>(`/workouts/${id}/recovery-target`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pre_exercise_weight_kg: pre || null, post_exercise_weight_kg: post || null }) });
export const generateMeals = (id: string) => request<{ recommendations: Meal[] }>(`/workouts/${id}/recommendations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
export const selectMeal = (id: string) => request<{ id: string; selected: boolean }>(`/recommendations/${id}/select`, { method: "POST" });

