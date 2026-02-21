import React from "react";
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/dashboard",   label: "HOME",     icon: "🏠" },
  { path: "/eyes",        label: "EYES",     icon: "👁️" },
  { path: "/admin-panel", label: "ADMIN",    icon: "⚙️" },
];

const Nav: React.FC = () => {
  return (
    <nav className="w-full status-bar flex-shrink-0">
      <div className="flex items-center gap-1 overflow-x-auto px-2 py-0">
        <span className="font-header text-zombie-green text-sm font-bold neon-text mr-3 whitespace-nowrap">
          KILO
        </span>
        <div className="flex gap-1">
          {NAV_ITEMS.map(({ path, label, icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                "flex items-center gap-1 px-3 py-1 text-xs font-header rounded transition-all whitespace-nowrap " +
                (isActive
                  ? "bg-zombie-green text-dark-bg shadow-lg shadow-zombie-green/40"
                  : "text-zombie-green hover:bg-dark-card hover:shadow-md hover:shadow-zombie-green/20 border border-transparent hover:border-zombie-green/40")
              }
            >
              <span>{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
};

export default Nav;
