"use client";

import { usePathname } from "next/navigation";
import { Activity, ArrowDownToLine, BookOpen, ChartNoAxesCombined, CircleHelp, Compass, Database, FileChartColumn, FunctionSquare, Gauge, Home, ListTree, Menu, Search, ShieldCheck, X } from "lucide-react";
import { useState } from "react";

const navigation = [
  { href: "/", label: "Overview", icon: Home, group: "Workspace" },
  { href: "/bonds", label: "Bond yields", icon: ChartNoAxesCombined, group: "Workspace" },
  { href: "/country-risk", label: "Country risk", icon: Gauge, group: "Workspace" },
  { href: "/cases", label: "Research cases", icon: BookOpen, group: "Research" },
  { href: "/demand", label: "HK / China demand", icon: Activity, group: "Research" },
  { href: "/indicators", label: "Indicators", icon: ListTree, group: "Reference" },
  { href: "/formulas", label: "Formulas", icon: FunctionSquare, group: "Reference" },
  { href: "/models", label: "Model workspace", icon: FileChartColumn, group: "Reference" },
  { href: "/history", label: "Data versions", icon: Database, group: "Reference" },
];

export function SiteFrame({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const current = navigation.find((item) => item.href === path) ?? navigation[0];
  const groups = [...new Set(navigation.map((item) => item.group))];
  return (
    <div className="site-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Compass size={19} strokeWidth={1.8} /></div>
          <div><span className="brand-title">Econ Research</span><span className="brand-subtitle">Private research hub</span></div>
          <button className="icon-button mobile-close" onClick={() => setMenuOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="workspace-pill"><ShieldCheck size={14} /><span>Owner private</span><i /></div>
        <nav aria-label="Primary navigation">
          {groups.map((group) => <div className="nav-group" key={group}>
            <p className="nav-heading">{group}</p>
            {navigation.filter((item) => item.group === group).map(({ href, label, icon: Icon }) => (
              <a key={href} href={href} onClick={() => setMenuOpen(false)} className={`nav-item ${current.href === href ? "is-active" : ""}`} aria-current={current.href === href ? "page" : undefined}>
                <Icon size={17} strokeWidth={1.8} /><span>{label}</span>{label === "Model workspace" && <span className="nav-pending">Soon</span>}
              </a>
            ))}
          </div>)}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note"><span className="pulse-dot"/><span>Versioned research snapshots</span></div>
          <p>Evidence first. Models run locally.</p>
        </div>
      </aside>
      {menuOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <div className="main-column">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMenuOpen(true)}><Menu size={20} /></button>
          <div className="crumb"><span>Econ Research</span><span className="crumb-sep">/</span><strong>{current.label}</strong></div>
          <div className="topbar-right"><span className="secure-label"><ShieldCheck size={15} /> Private workspace</span><button className="icon-button" aria-label="Search is not available yet" title="Search is not available yet"><Search size={17} /></button><button className="avatar" aria-label="Signed-in owner">CT</button></div>
        </header>
        <main className="page-content">{children}</main>
        <footer className="site-footer"><span>Source definitions vary across countries. Missing observations remain blank.</span><a href="/help"><CircleHelp size={14} /> About the data</a><a href="/history"><ArrowDownToLine size={14} /> Versions & downloads</a></footer>
      </div>
    </div>
  );
}
