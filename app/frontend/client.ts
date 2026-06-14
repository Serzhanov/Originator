import { createORPCClient } from "@orpc/client"
import { RPCLink } from "@orpc/client/fetch"
import type { RouterClient } from "@orpc/server"

import type { ApiRouter } from "../backend/api/index.js"

export function createClient(): RouterClient<ApiRouter> {
  const link = new RPCLink({ url: new URL("/_rpc", window.location.origin).href })
  return createORPCClient(link) as RouterClient<ApiRouter>
}
