import { BarChart3, BookOpen, Calculator, Database, FileText, GitBranch, Home, LineChart, ListTree, Network, UploadCloud } from "lucide-react";

export type PageKey = "home" | "cases" | "event" | "dataset" | "imf" | "indicators" | "regression" | "forecasting" | "var" | "formulas" | "memo" | "lessons";

const items: { key: PageKey; label: string; icon: React.ComponentType<{ size?: number }> }[] = [
  { key: "home", label: "Home", icon: Home },
  { key: "cases", label: "Research Cases", icon: BookOpen },
  { key: "event", label: "Historical Event Lab", icon: Network },
  { key: "dataset", label: "Dataset", icon: Database },
  { key: "imf", label: "IMF Data Connector", icon: UploadCloud },
  { key: "indicators", label: "Indicator Registry", icon: ListTree },
  { key: "regression", label: "Regression Lab", icon: BarChart3 },
  { key: "forecasting", label: "Forecasting Lab", icon: LineChart },
  { key: "var", label: "Vector Autoregression Lab", icon: GitBranch },
  { key: "formulas", label: "Formula Playground", icon: Calculator },
  { key: "memo", label: "Model Review", icon: FileText },
  { key: "lessons", label: "Lessons", icon: BookOpen }
];

export function Sidebar({ active, onNavigate }: { active: PageKey; onNavigate: (page: PageKey) => void }) {
  return (
    <aside className="sidebar">
      <div className="brand">Risk Research Lab<small>Country Risk + Market Risk</small></div>
      <nav>
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.key} className={active === item.key ? "nav active" : "nav"} onClick={() => onNavigate(item.key)}>
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
