import { useEffect, useState, type MouseEvent, type ReactNode } from "react";

export function navigate(path: string) { history.pushState({}, "", path); window.dispatchEvent(new PopStateEvent("popstate")); window.scrollTo({ top: 0, behavior: "smooth" }); }
export function usePath() { const [path, setPath] = useState(location.pathname); useEffect(() => { const update = () => setPath(location.pathname); addEventListener("popstate", update); return () => removeEventListener("popstate", update); }, []); return path; }
export function Link({ to, children, className }: { to: string; children: ReactNode; className?: string }) { const click = (event: MouseEvent<HTMLAnchorElement>) => { if (!event.metaKey && !event.ctrlKey) { event.preventDefault(); navigate(to); } }; return <a href={to} onClick={click} className={className}>{children}</a>; }
