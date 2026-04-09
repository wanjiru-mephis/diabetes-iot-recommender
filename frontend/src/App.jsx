import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Upload from './pages/Upload.jsx'
import Trends from './pages/Trends.jsx'
import Recommendations from './pages/Recommendations.jsx'

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Diabetes IoT</h1>
        <div className="sub">Treatment Support</div>
        <nav>
          <NavLink to="/dashboard" className={({isActive}) => isActive ? 'active' : ''}>Dashboard</NavLink>
          <NavLink to="/upload" className={({isActive}) => isActive ? 'active' : ''}>Upload Data</NavLink>
          <NavLink to="/trends" className={({isActive}) => isActive ? 'active' : ''}>Trends</NavLink>
          <NavLink to="/recommendations" className={({isActive}) => isActive ? 'active' : ''}>Recommendations</NavLink>
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
