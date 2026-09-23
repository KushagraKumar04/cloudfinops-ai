import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { Dashboard } from './pages/Dashboard'
import { Costs } from './pages/Costs'
import { Resources } from './pages/Resources'
import { Recommendations } from './pages/Recommendations'
import { RecommendationDetail } from './pages/RecommendationDetail'
import { Analyst } from './pages/Analyst'
import { Forecast } from './pages/Forecast'
import { Approvals } from './pages/Approvals'
import { Audit } from './pages/Audit'
import { CloudAccounts } from './pages/CloudAccounts'
import { Settings } from './pages/Settings'
import { NotFound } from './pages/NotFound'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/costs" element={<Costs />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/recommendations/:id" element={<RecommendationDetail />} />
        <Route path="/analyst" element={<Analyst />} />
        <Route path="/forecast" element={<Forecast />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/cloud-accounts" element={<CloudAccounts />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}