import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ChatSessionListResult } from './sessionTypes'
import {
  createSession,
  deleteSession,
  getSession,
  listSessions,
} from './sessionApi'

export const sessionKeys = {
  all: ['chatSessions'] as const,
  list: () => [...sessionKeys.all, 'list'] as const,
  detail: (id: string) => [...sessionKeys.all, 'detail', id] as const,
}

export function useSessions() {
  return useQuery({ queryKey: sessionKeys.list(), queryFn: listSessions })
}

export function useSession(id: string | undefined) {
  return useQuery({
    queryKey: sessionKeys.detail(id ?? ''),
    queryFn: () => getSession(id as string),
    enabled: Boolean(id),
  })
}

export function useCreateSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (title?: string) => createSession(title),
    onSuccess: () => qc.invalidateQueries({ queryKey: sessionKeys.all }),
  })
}

export function useDeleteSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteSession(id),
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: sessionKeys.list() })
      const previous = qc.getQueryData<ChatSessionListResult>(sessionKeys.list())
      if (previous) {
        qc.setQueryData<ChatSessionListResult>(sessionKeys.list(), {
          items: previous.items.filter((s) => s.id !== id),
          total: Math.max(0, previous.total - 1),
        })
      }
      return { previous }
    },
    onError: (_err, _id, ctx) => {
      const previous = (ctx as { previous?: ChatSessionListResult } | undefined)?.previous
      if (previous) {
        qc.setQueryData(sessionKeys.list(), previous)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}