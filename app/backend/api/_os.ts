import { os as globalOs } from "@orpc/server"

import { type Context } from "./index.js"

export const os = globalOs.$context<Context>().use(async ({ context, next, path }, input) => {
  if (path.length === 0 || path[0] !== "_control") {
    context.model.apply({
      type: "apiCalled",
      path: path.join("."),
      input: input !== undefined ? JSON.parse(JSON.stringify(input)) : null,
    })
  }

  const result = await next()
  return result
})
