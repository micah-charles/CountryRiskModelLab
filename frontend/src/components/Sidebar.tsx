import { BarChart3, BookOpen, Database, FileText, Home, LineChart, Settings, UploadCloud } from "lucide-react";

export type PageKey = "home" | "dataset" | "imf" | "regression" | "forecasting" | "var" | "memo" | "lessons";

const items: { key: PageKey; label: string; icon: React.ComponentType<{ size?: number }> }[] = [
  { key: "home", label: "Home", icon: Home },
  { key: "dataset", label: "Dataset", icon: Database },
  { key: "imf", label: "IMF Data Connector", icon: UploadCloud },
  { key: "regression", label: "Regression Lab", icon: BarChart3 },
  { key: "forecasting", label: "Forecasting Lab", icon: LineChart },
  { key: "var", label: "VAR Lab", icon: Settings },
  { key: "memo", label: "Model Review", icon: FileText },
  { key: "lessons", label: "Admin Lessons", icon: BookOpen }
];

export function Sidebar({ active, onNavigate }: { active: PageKey; onNavigate: (page: PageKey) => void }) {
  return (
    <aside className="sidebar">
      <div className="brand">Country Risk Statistical Model Lab</div>
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

