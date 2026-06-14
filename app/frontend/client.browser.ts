import { createRouterClient, type RouterClient } from "@orpc/server"

import { apiModel, apiRouter, type ApiRouter } from "../backend/api/index.js"

export function createClient(): RouterClient<ApiRouter> {
  return createRouterClient(apiRouter, { context: { model: apiModel } })
}
