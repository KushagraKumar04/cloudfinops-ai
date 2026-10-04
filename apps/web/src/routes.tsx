import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { ProtectedRoute } from './features/auth/ProtectedRoute'
import { Dashboard } from './pages/Dashboard'
import { Costs } from './pages/Costs'
import { Resources } from './pages/Resources'
import { ResourceDetail } from './pages/ResourceDetail'
import { Recommendations } from './pages/Recommendations'
import { RecommendationDetail } from './pages/RecommendationDetail'
import { Analyst } from './pages/Analyst'
import { Forecast } from './pages/Forecast'
import { Approvals } from './pages/Approvals'
import { Audit } from './pages/Audit'
import { CloudAccounts } from './pages/CloudAccounts'
import { Kubernetes } from './pages/Kubernetes'
import { KubernetesCluster } from './pages/KubernetesCluster'
import { Commitments } from './pages/Commitments'
import { Team } from './pages/Team'
import { Notifications } from './pages/Notifications'
import { Settings } from './pages/Settings'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { Terms } from './pages/Terms'
import { Privacy } from './pages/Privacy'
import { NotFound } from './pages/NotFound'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/privacy" element={<Privacy />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/costs" element={<Costs />} />
          <Route path="/resources" element={<Resources />} />
          <Route path="/resources/:id" element={<ResourceDetail />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/recommendations/:id" element={<RecommendationDetail />} />
          <Route path="/analyst" element={<Analyst />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/cloud-accounts" element={<CloudAccounts />} />
          <Route path="/kubernetes" element={<Kubernetes />} />
          <Route path="/kubernetes" element={<Kubernetes />} />
          <Route path="/kubernetes/:id" element={<KubernetesCluster />} />
          <Route path="/commitments" element={<Commitments />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/team" element={<Team />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  )
}