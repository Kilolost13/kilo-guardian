import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import Dashboard from "./pages/Dashboard";
import Admin from "./pages/Admin";
import UserDashboard from "./pages/UserDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import Nav from "./components/Nav";
import "./App.css";

function App() {
  return (
    <Router basename="/guardian">
      <div className="scanline" />

      <div className="flex flex-col h-screen w-full bg-dark-bg grid-bg">
        <Nav />

        <div className="flex-1 overflow-y-auto">
          <Routes>
            {/* Home goes to Dashboard (chat interface) */}
            <Route path="/"            element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"   element={<Dashboard />} />
            <Route path="/chat"        element={<ChatPage />} />

            {/* Eyes tab - UserDashboard with all data */}
            <Route path="/eyes"        element={<UserDashboard />} />
            <Route path="/user"        element={<UserDashboard />} />

            {/* Admin */}
            <Route path="/admin-panel" element={<AdminDashboard />} />
            <Route path="/admin"       element={<Admin />} />

            {/* Fallback */}
            <Route path="*"            element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
