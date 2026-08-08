import { useEffect, useMemo, useState } from "react";
import * as api from "./api";
import type { Activity, Inventory, Meal, Profile, Recovery, Workout } from "./types";

const activities: Activity[] = ["cycling", "running", "walking", "hiking", "unknown"];
const emptyProfile: Omit<Profile, "id"> = { age: 30, sex: "prefer_not_to_say", height_cm: 170, weight_kg: 70, fitness_goal: "maintain_weight", foods_to_avoid: [], favorite_foods: [], max_prep_minutes: 20, unit_preference: "metric" };

function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<Omit<Profile, "id">>(emptyProfile);
  const [inventory, setInventory] = useState<Inventory[]>([]);
  const [workout, setWorkout] = useState<Workout | null>(null);
  const [recovery, setRecovery] = useState<Recovery | null>(null);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [tab, setTab] = useState("profile");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [heightInput, setHeightInput] = useState("170");
  const [weightInput, setWeightInput] = useState("70");
  const [newFood, setNewFood] = useState("");
  const [preWeight, setPreWeight] = useState("");
  const [postWeight, setPostWeight] = useState("");
  const [activity, setActivity] = useState<Activity>("unknown");
  const [durationMinutes, setDurationMinutes] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => { api.getProfile().then(p => { setProfile(p); setForm(p); setInputs(p); }).catch(() => undefined); api.getInventory().then(setInventory).catch(() => undefined); }, []);
  const setInputs = (p: Profile) => { setHeightInput(p.unit_preference === "imperial" ? String(Math.round(p.height_cm / 2.54 / 0.1) / 10) : String(p.height_cm)); setWeightInput(p.unit_preference === "imperial" ? String(Math.round(p.weight_kg * 2.20462 * 10) / 10) : String(p.weight_kg)); };
  const updateForm = <K extends keyof Omit<Profile, "id">>(key: K, value: Omit<Profile, "id">[K]) => setForm(current => ({ ...current, [key]: value }));
  const save = async () => { try { setError(""); const metricHeight = form.unit_preference === "imperial" ? Number(heightInput) * 2.54 : Number(heightInput); const metricWeight = form.unit_preference === "imperial" ? Number(weightInput) / 2.20462 : Number(weightInput); const saved = await api.saveProfile({ ...form, height_cm: metricHeight, weight_kg: metricWeight }); setProfile(saved); setForm(saved); setInputs(saved); setMessage("Profile saved."); } catch (e) { setError((e as Error).message); } };
  const addFood = async () => { if (!newFood.trim()) return; try { const item = await api.addInventory(newFood); setInventory([...inventory, item]); setNewFood(""); } catch (e) { setError((e as Error).message); } };
  const upload = async (file?: File) => {
    if (!file) return;
    try {
      setError("");
      setIsUploading(true);
      const w = await api.uploadWorkout(file);
      setWorkout(w);
      setActivity((w.activity_type as Activity) || "unknown");
      setDurationMinutes(w.duration_seconds ? String(Math.round(w.duration_seconds / 60)) : "");
      setRecovery(null);
      setMeals([]);
      setTab("workout");
      setShowUploadModal(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsUploading(false);
    }
  };
  const correct = async () => { if (!workout || !durationMinutes || activity === "unknown") return; try { const w = await api.correctWorkout(workout.id, activity, Math.round(Number(durationMinutes) * 60)); setWorkout(w); setMessage("Workout correction saved."); } catch (e) { setError((e as Error).message); } };
  const recover = async () => { if (!workout) return; try { const r = await api.calculateRecovery(workout.id, preWeight ? Number(preWeight) : undefined, postWeight ? Number(postWeight) : undefined); setRecovery(r); setTab("recommendations"); } catch (e) { setError((e as Error).message); } };
  const recommend = async () => { if (!workout) return; try { setIsGenerating(true); setError(""); const result = await api.generateMeals(workout.id); setMeals(result.recommendations); } catch (e) { setError((e as Error).message); } finally { setIsGenerating(false); } };
  const selected = useMemo(() => meals.find(m => m.selected)?.id, [meals]);
  const choose = async (id: string) => { try { await api.selectMeal(id); setMeals(meals.map(m => ({ ...m, selected: m.id === id }))); } catch (e) { setError((e as Error).message); } };
  const formatDistance = (meters: number | null) => meters == null ? "—" : form.unit_preference === "imperial" ? `${(meters / 1609.34).toFixed(2)} mi` : `${(meters / 1000).toFixed(2)} km`;
  const needsCorrection = workout ? activity !== workout.activity_type || (durationMinutes ? Math.round(Number(durationMinutes) * 60) : null) !== workout.duration_seconds : true;
  const tabs = [["profile", "Profile"], ["inventory", "Available food"], ["workout", "Workout"], ["recommendations", "Recommendations"]];

  return <div className="shell"><header><div><p className="eyebrow">POST-WORKOUT</p><h1>Recovery meal</h1><p className="subtle">A practical next meal based on the workout you actually completed.</p></div><div className="status">{profile ? "Profile ready" : "Set up your profile"}</div></header>
    <nav>{tabs.map(([key, label]) => <button className={tab === key ? "active" : ""} onClick={() => setTab(key)} key={key}>{label}</button>)}</nav>
    {error && <div className="alert error">{error}</div>}{message && <div className="alert success">{message}</div>}
    {tab === "profile" && <section className="card"><h2>Your profile</h2><div className="grid two"><label>Age<input type="number" value={form.age} onChange={e => updateForm("age", Number(e.target.value))} /></label><label>Sex<select value={form.sex} onChange={e => updateForm("sex", e.target.value as Profile["sex"])}><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option><option value="prefer_not_to_say">Prefer not to say</option></select></label><label>Units<select value={form.unit_preference} onChange={e => { const unit = e.target.value as "metric" | "imperial"; const currentMetricHeight = form.unit_preference === "imperial" ? Number(heightInput) * 2.54 : Number(heightInput); const currentMetricWeight = form.unit_preference === "imperial" ? Number(weightInput) / 2.20462 : Number(weightInput); setHeightInput(unit === "imperial" ? String(Math.round(currentMetricHeight / 2.54 * 10) / 10) : String(Math.round(currentMetricHeight * 10) / 10)); setWeightInput(unit === "imperial" ? String(Math.round(currentMetricWeight * 2.20462 * 10) / 10) : String(Math.round(currentMetricWeight * 10) / 10)); updateForm("unit_preference", unit); }}>{/* conversion occurs on save */}<option value="metric">Metric</option><option value="imperial">Imperial</option></select></label><label>Height ({form.unit_preference === "metric" ? "cm" : "in"})<input type="number" value={heightInput} onChange={e => setHeightInput(e.target.value)} /></label><label>Weight ({form.unit_preference === "metric" ? "kg" : "lb"})<input type="number" value={weightInput} onChange={e => setWeightInput(e.target.value)} /></label><label>Fitness goal<select value={form.fitness_goal} onChange={e => updateForm("fitness_goal", e.target.value as Profile["fitness_goal"])}><option value="maintain_weight">Maintain weight</option><option value="lose_weight">Lose weight</option><option value="gain_muscle">Gain muscle</option><option value="endurance_performance">Endurance performance</option></select></label><label>Maximum prep time (minutes)<input type="number" min="1" max="120" value={form.max_prep_minutes ?? ""} onChange={e => updateForm("max_prep_minutes", e.target.value ? Number(e.target.value) : null)} /></label><label>Favorite foods<input value={form.favorite_foods.join(", ")} onChange={e => updateForm("favorite_foods", e.target.value.split(","))} placeholder="rice, yogurt, bananas" /></label><label>Foods to avoid<input value={form.foods_to_avoid.join(", ")} onChange={e => updateForm("foods_to_avoid", e.target.value.split(","))} placeholder="peanuts, shellfish" /></label></div><button className="primary" onClick={save}>Save profile</button></section>}
    {tab === "inventory" && <section className="card"><h2>Available food</h2><p className="subtle">Names are matched by food category, so chicken can match chicken breast.</p><div className="inline"><input value={newFood} onChange={e => setNewFood(e.target.value)} placeholder="e.g. chicken breast" onKeyDown={e => e.key === "Enter" && addFood()} /><button className="primary" onClick={addFood}>Add food</button></div><div className="chips">{inventory.map(item => <span className="chip" key={item.id}>{item.name}<button onClick={async () => { await api.deleteInventory(item.id); setInventory(inventory.filter(i => i.id !== item.id)); }}>×</button></span>)}</div></section>}
    {tab === "workout" && <section className="card"><div className="card-header"><h2>Review workout</h2><button className="secondary" onClick={() => setShowUploadModal(true)} type="button">Upload workout</button></div>{!workout ? <p>Upload a workout first.</p> : <><div className="stats"><div><small>Distance</small><strong>{formatDistance(workout.distance_meters)}</strong></div><div><small>Intensity</small><strong>{workout.intensity ?? "Needs correction"}</strong></div><div><small>Energy estimate</small><strong>{workout.estimated_calories ? `${workout.estimated_calories.low}–${workout.estimated_calories.high} kcal` : "—"}</strong></div></div><div className="grid two"><label>Activity<select value={activity} onChange={e => setActivity(e.target.value as Activity)}>{activities.map(a => <option key={a}>{a}</option>)}</select></label><label>Duration (minutes)<input type="number" min="1" value={durationMinutes} onChange={e => setDurationMinutes(e.target.value)} /></label></div><button className="secondary" onClick={correct} disabled={activity === "unknown" || !durationMinutes}>Confirm</button>{needsCorrection && <p className="fineprint">Save activity or duration corrections before calculating.</p>}<hr /><h3>Optional hydration measurement</h3><div className="grid two"><label>Pre-workout weight (kg)<input type="number" value={preWeight} onChange={e => setPreWeight(e.target.value)} /></label><label>Post-workout weight (kg)<input type="number" value={postWeight} onChange={e => setPostWeight(e.target.value)} /></label></div><button className="primary" onClick={recover} disabled={!workout.intensity || activity === "unknown" || needsCorrection}>Calculate recovery target</button><p className="fineprint">Workout energy and recovery values are estimates for general fitness guidance, not medical advice.</p></>}</section>}
    {showUploadModal && <div className="modal-backdrop"><div className="modal"><div className="modal-header"><h2>Upload workout</h2><button className="secondary" type="button" onClick={() => setShowUploadModal(false)}>Cancel</button></div><p className="subtle">Choose a GPX file and the app will parse it for review.</p><label className="drop">{isUploading ? "Waiting for file upload…" : "Choose a GPX file"}<input type="file" accept=".gpx,application/gpx+xml" disabled={isUploading} onChange={e => upload(e.target.files?.[0])} /></label>{isUploading && <p className="subtle">Uploading workout…</p>}</div></div>}
    {tab === "recommendations" && <section className="card">{!recovery ? <p>Calculate a recovery target first.</p> : <><h2>Your recovery target</h2><div className="target"><span>Protein <b>{recovery.protein_g.low}–{recovery.protein_g.high} g</b></span><span>Carbohydrates <b>{recovery.carbs_g.low}–{recovery.carbs_g.high} g</b></span><span>Fluids <b>{recovery.fluid_ml ? `${recovery.fluid_ml.low}–${recovery.fluid_ml.high} ml` : "No measured-loss target"}</b></span></div><button className="primary" onClick={recommend} disabled={isGenerating}>{isGenerating ? "Generating recommendations…" : "Generate recommendations"}</button>{isGenerating && <p className="subtle">Please wait while recommendations are being generated.</p>}{meals.length > 0 && <div className="meal-grid">{meals.map(meal => <article className={`meal ${selected === meal.id ? "chosen" : ""}`} key={meal.id}><p className="eyebrow">{meal.category.split("_").join(" ")}</p><h3>{meal.name}</h3><p className="nutrition">{meal.estimated_calories} kcal · {meal.protein_g}g protein · {meal.carbs_g}g carbs · {meal.fat_g}g fat</p><p>{meal.rationale}</p><p><b>{meal.prep_minutes} min</b></p><ul>{meal.ingredients.map(i => <li key={`${meal.id}-${i.name}`}>{i.quantity} {i.unit} {i.name} {i.available ? <span className="available">available</span> : <span className="missing">missing</span>}</li>)}</ul>{meal.preparation_steps.map((step, i) => <p className="step" key={step}>{i + 1}. {step}</p>)}{meal.missing_ingredients.length > 0 && <p className="missing">Missing: {meal.missing_ingredients.join(", ")}</p>}<button className={meal.selected ? "selected" : "secondary"} onClick={() => choose(meal.id)}>{meal.selected ? "Selected" : "Choose this meal"}</button></article>)}</div>}</>}</section>}
    <footer>Estimates are approximate. This app provides general fitness and nutrition guidance and is not medical advice.</footer>
  </div>;
}
export default App;
