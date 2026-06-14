import { existsSync } from "node:fs"
import { join } from "node:path"

import fastifyStatic from "@fastify/static"
import { OpenAPIHandler } from "@orpc/openapi/fastify"
import { OpenAPIReferencePlugin } from "@orpc/openapi/plugins"
import { onError } from "@orpc/server"
import { RPCHandler } from "@orpc/server/fastify"
import { CORSPlugin } from "@orpc/server/plugins"
import { ZodToJsonSchemaConverter } from "@orpc/zod/zod4"
import fastify from "fastify"

import { apiModel, apiRouter } from "./api/index.js"

async function main() {
  const context = {
    model: apiModel,
  }

  const cors = new CORSPlugin({
    origin: origin => origin,
    allowMethods: ["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"],
  })

  const rpcHandler = new RPCHandler(apiRouter, {
    plugins: [cors],
    interceptors: [onError(error => console.error(error))],
  })

  const openApiHandler = new OpenAPIHandler(apiRouter, {
    plugins: [
      cors,
      new OpenAPIReferencePlugin({
        docsProvider: "scalar",
        schemaConverters: [new ZodToJsonSchemaConverter()],
        specGenerateOptions: {
          info: {
            title: "Excalidraw",
            version: "1.0.0",
          },
        },
      }),
    ],
    interceptors: [onError(error => console.error(error))],
  })

  const app = fastify()

  app.addContentTypeParser("*", (_request, _payload, done) => {
    done(null, undefined)
  })

  for (const [prefix, handler] of [
    ["/_rpc", rpcHandler],
    ["/_openapi", openApiHandler],
  ] as const) {
    console.log(`Registering handler for prefix: ${prefix}/*`)
    app.all(`${prefix}*`, async (req, reply) => {
      const { matched } = await handler.handle(req, reply, {
        prefix,
        context,
      })

      if (!matched) {
        reply.status(404).send("Not found")
      }
    })
  }

  // Serve static frontend from dist/ directory (Vite build output)
  const frontendDist = process.env["FRONTEND_DIST"]
  if (frontendDist) {
    const distPath = join(import.meta.dirname, "..", frontendDist)
    if (existsSync(distPath)) {
      console.log(`Serving static files from: ${distPath}`)
      await app.register(fastifyStatic, {
        root: distPath,
        prefix: "/",
      })
    } else {
      console.warn(`Frontend dist directory not found: ${distPath}`)
    }
  }

  const port = parseInt(process.env["PORT"] ?? "31464", 10)

  try {
    await app.listen({ host: "0.0.0.0", port })
    console.log(`Listening on port ${port}`)
  } catch (err) {
    console.error(err)
    process.exit(1)
  }
}

void main()
