import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/features/auth/useAuth'
import { Skeleton } from '@/components/ui/Skeleton'

export function SuperuserRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }

  if (!user?.isSuperuser) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}