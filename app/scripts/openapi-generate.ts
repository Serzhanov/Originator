import { OpenAPIGenerator } from "@orpc/openapi"
import { ZodToJsonSchemaConverter } from "@orpc/zod/zod4"

import { apiRouter } from "../backend/api/index.js"

const generator = new OpenAPIGenerator({
  schemaConverters: [new ZodToJsonSchemaConverter()],
})

const spec = await generator.generate(apiRouter, {
  info: {
    title: "Excalidraw",
    version: "1.0.0",
  },
})

console.log(JSON.stringify(spec, null, 2))
