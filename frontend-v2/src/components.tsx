import { useEffect, useState, type ReactNode } from "react";
import * as api from "./api";
import { Link } from "./router";
import type { Account, Meal } from "./types";

const nav = [
  ["/", "⌂", "Home"], ["/get-meal", "♨", "Get Meal"], ["/pantry", "▣", "Pantry"],
  ["/favorites", "♡", "Favorites"], ["/progress", "▥", "Progress"],
];

export function Layout({ path, children }: { path: string; children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  useEffect(() => { api.getAccount().then(setAccount).catch(() => undefined); }, [path]);
  const active = (href: string) => href === "/" ? path === "/" : path.startsWith(href) || (href === "/get-meal" && path.startsWith("/meals/"));
  const initials = (account?.display_name || "Athlete").split(/\s+/).map(x => x[0]).slice(0, 2).join("").toUpperCase();
  return <div className="app-shell">
    <aside className="sidebar">
      <Link to="/" className="brand"><span className="brand-mark">♨</span><span>Recovery<br /><b>Meal</b></span></Link>
      <nav className="side-nav">{nav.map(([href, icon, label]) => <Link key={href} to={href} className={active(href) ? "active" : ""}><span>{icon}</span>{label}</Link>)}</nav>
      <div className="side-spacer" />
      <div className="streak-mini"><span className="flame">◆</span><div><b>Build your streak</b><small>One recovery meal at a time.</small></div></div>
      <Link to="/profile" className={`account-mini ${path === "/profile" ? "active" : ""}`}>
        {account?.avatar_url ? <img src={api.imageUrl(account.avatar_url) || ""} alt="" /> : <span className="avatar">{initials}</span>}
        <span><b>{account?.display_name || "Athlete"}</b><small>View profile</small></span><i>›</i>
      </Link>
    </aside>
    <main className="main-content">{children}</main>
    <nav className="mobile-nav">{nav.map(([href, icon, label]) => <Link key={href} to={href} className={active(href) ? "active" : ""}><span>{icon}</span><small>{label}</small></Link>)}</nav>
  </div>;
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return <header className="page-header"><div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</header>;
}

export function Stepper({ step }: { step: 1 | 2 | 3 }) {
  return <div className="stepper">{["Upload workout", "Review workout", "Meal options"].map((label, index) => { const n = index + 1; return <div className={n === step ? "current" : n < step ? "done" : ""} key={label}><span>{n < step ? "✓" : n}</span><b>{label}</b></div>; })}</div>;
}

export function Loader({ label = "Loading" }: { label?: string }) { return <div className="loader"><span />{label}…</div>; }
export function Notice({ children, type = "info" }: { children: ReactNode; type?: "info" | "error" | "success" }) { return <div className={`notice ${type}`}>{children}</div>; }
export function Empty({ icon = "♨", title, body, action }: { icon?: string; title: string; body: string; action?: ReactNode }) { return <div className="empty"><span>{icon}</span><h2>{title}</h2><p>{body}</p>{action}</div>; }

export function MealPhoto({ meal, className = "" }: { meal: Pick<Meal, "name" | "image_url" | "image_status">; className?: string }) {
  const src = api.imageUrl(meal.image_url);
  return <div className={`meal-photo ${className} ${meal.image_status === "generating" ? "shimmer" : ""}`}>
    {src ? <img src={src} alt={meal.name} /> : <div className="photo-fallback"><span>♨</span><small>{meal.image_status === "generating" ? "Creating your meal photo" : "Fresh recovery meal"}</small></div>}
  </div>;
}

export function Stat({ icon, label, value }: { icon: string; label: string; value: ReactNode }) { return <div className="stat"><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></div>; }

const mealOptionBadges: Record<string, string> = {
  best_recovery_match: "★ Best for recovery",
  fastest: "◷ Fastest",
  best_use_of_inventory: "▣ Best use of inventory",
};

export function MealCard({ meal, featured = false, onSelect, onFavorite }: { meal: Meal; featured?: boolean; onSelect: () => void; onFavorite: () => void }) {
  const badge = mealOptionBadges[meal.category];
  return <article className={`meal-card ${featured ? "featured" : ""}`}>
    <MealPhoto meal={meal} />
    <div className="meal-card-body">{badge && <span className="best-badge">{badge}</span>}<div className="meal-title-row"><h2>{meal.name}</h2><button className={`icon-button ${meal.favorite ? "liked" : ""}`} onClick={onFavorite} aria-label="Toggle favorite">{meal.favorite ? "♥" : "♡"}</button></div>
      <div className="macro-row"><span>◷ <b>{meal.prep_minutes}</b> min</span><span>♨ <b>{meal.estimated_calories}</b> kcal</span><span>◡ <b>{meal.protein_g}</b>g protein</span><span>⌁ <b>{meal.carbs_g}</b>g carbs</span></div>
      <div className="fit-row"><span>● Recovery fit</span><b>{meal.recovery_match_score >= 1 ? "Excellent" : meal.recovery_match_score >= .8 ? "Very good" : "Good"}</b></div>
      <div className="fit-row"><span>● Ingredients</span><b>{meal.missing_ingredients.length ? `${meal.missing_ingredients.length} missing` : "All on hand"}</b></div>
      <p className="rationale">{meal.rationale}</p>
      <div className="card-actions"><Link to={`/meals/${meal.id}`} className="button secondary">View recipe</Link><button className="button primary" onClick={onSelect}>{meal.selected ? "✓ I'm making this" : "Select meal"}</button></div>
    </div>
  </article>;
}
