import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  DollarSign,
  Server,
  Lightbulb,
  MessageSquare,
  TrendingUp,
  CheckSquare,
  History,
  Cloud,
  Settings as SettingsIcon,
  Boxes,
  BadgeDollarSign,
  Bell,
} from 'lucide-react'

const items = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/costs', label: 'Costs', icon: DollarSign },
  { to: '/resources', label: 'Resources', icon: Server },
  { to: '/recommendations', label: 'Recommendations', icon: Lightbulb },
  { to: '/analyst', label: 'AI Analyst', icon: MessageSquare },
  { to: '/forecast', label: 'Forecast', icon: TrendingUp },
  { to: '/approvals', label: 'Approvals', icon: CheckSquare },
  { to: '/audit', label: 'Audit', icon: History },
  { to: '/kubernetes', label: 'Kubernetes', icon: Boxes },
  { to: '/commitments', label: 'Commitments', icon: BadgeDollarSign },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/cloud-accounts', label: 'Cloud Accounts', icon: Cloud },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

export function Sidebar() {
  return (
    <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r border-border bg-canvas">
      <div className="flex h-14 items-center gap-2 px-5 border-b border-border">
        <div className="h-6 w-6 rounded-sm bg-accent" aria-hidden />
        <span className="text-sm font-semibold tracking-tight">CloudFinOps AI</span>
      </div>
      <nav className="flex-1 px-2 py-3">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 rounded px-2.5 py-1.5 text-sm transition-colors',
                isActive
                  ? 'bg-surface text-ink font-medium border border-border'
                  : 'text-ink-muted hover:text-ink hover:bg-surface-muted border border-transparent',
              )
            }
          >
            <Icon size={16} strokeWidth={1.75} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-3 border-t border-border text-[11px] text-ink-subtle">
        <div className="flex items-center justify-between">
          <span>Demo data · v0.1</span>
          <span className="flex items-center gap-1.5">
            <NavLink to="/terms" className="hover:text-ink transition-colors">Terms</NavLink>
            <span aria-hidden>·</span>
            <NavLink to="/privacy" className="hover:text-ink transition-colors">Privacy</NavLink>
          </span>
        </div>
      </div>
    </aside>
  )
}