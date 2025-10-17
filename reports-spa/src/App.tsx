import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout/Layout'
import TeamSprintDashboard from '@/pages/TeamSprintDashboard'
import TeamKpiDashboard from '@/pages/TeamKpiDashboard'
import DeveloperActivityDashboard from '@/pages/DeveloperActivityDashboard'
import DeveloperComparisonDashboard from '@/pages/DeveloperComparisonDashboard'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<TeamSprintDashboard />} />
          <Route path="/kpi" element={<TeamKpiDashboard />} />
          <Route path="/activity" element={<DeveloperActivityDashboard />} />
          <Route path="/comparison" element={<DeveloperComparisonDashboard />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
