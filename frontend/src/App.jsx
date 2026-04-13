import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Upload from './pages/Upload.jsx'
import Trends from './pages/Trends.jsx'
import Recommendations from './pages/Recommendations.jsx'

const IconActivity = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
)

const IconGrid = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
  </svg>
)

const IconUpload = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 16 12 12 8 16" />
    <line x1="12" y1="12" x2="12" y2="21" />
    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
  </svg>
)

const IconTrending = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
)

const IconLightbulb = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="9" y1="18" x2="15" y2="18" />
    <line x1="10" y1="22" x2="14" y2="22" />
    <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8A6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
  </svg>
)

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <IconActivity />
          </div>
          <div className="sidebar-brand-text">
            <h1>Diabetes IoT</h1>
            <div className="sub">Treatment Support</div>
          </div>
        </div>

        <div className="sidebar-divider" />

        <nav>
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>
            <IconGrid /> Dashboard
          </NavLink>
          <NavLink to="/upload" className={({ isActive }) => isActive ? 'active' : ''}>
            <IconUpload /> Upload Data
          </NavLink>
          <NavLink to="/trends" className={({ isActive }) => isActive ? 'active' : ''}>
            <IconTrending /> Trends
          </NavLink>
          <NavLink to="/recommendations" className={({ isActive }) => isActive ? 'active' : ''}>
            <IconLightbulb /> Recommendations
          </NavLink>
        </nav>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/recommendations" element={<Recommendations />} />
        </Routes>
      </main>
    </div>
  )
}
