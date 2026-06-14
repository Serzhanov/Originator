import type { RouterClient } from "@orpc/server"
import { createTanstackQueryUtils } from "@orpc/tanstack-query"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import * as React from "react"

import type { ApiRouter } from "../backend/api/index.js"
import { createClient } from "./client.js"

export interface OrpcProps {
  children?: React.ReactNode
}

function createOrpc() {
  const client: RouterClient<ApiRouter> = createClient()
  const orpc = createTanstackQueryUtils(client)

  return { client, orpc }
}

type OrpcBundle = ReturnType<typeof createOrpc>

interface OrpcContextType {
  client: OrpcBundle["client"]
  orpc: OrpcBundle["orpc"]
  queryClient: QueryClient
}

const OrpcContext = React.createContext<OrpcContextType | null>(null)

export const Orpc: React.FC<OrpcProps> = ({ children }) => {
  const [queryClient] = React.useState(() => new QueryClient({ defaultOptions: { mutations: { gcTime: 0 } } }))
  const [{ client, orpc }] = React.useState(createOrpc)

  return (
    <QueryClientProvider client={queryClient}>
      <OrpcContext.Provider value={{ client, orpc, queryClient }}>{children}</OrpcContext.Provider>
    </QueryClientProvider>
  )
}

export function useOrpc(): OrpcContextType {
  const value = React.useContext(OrpcContext)
  if (!value) {
    throw new Error("useOrpc must be used within an OrpcProvider")
  }

  return value
}
