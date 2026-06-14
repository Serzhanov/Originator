import { eventIterator } from "@orpc/server"
import { z } from "zod"

import { model } from "./_models.js"
import { os } from "./_os.js"

const sceneStateSchema = z.object({
  elements: z.array(z.record(z.string(), z.unknown())),
  appState: z.record(z.string(), z.unknown()),
  files: z.record(z.string(), z.unknown()),
})

const controlModel = model
  .state({
    schema: sceneStateSchema,
    initial: { elements: [], appState: {}, files: {} } as z.infer<typeof sceneStateSchema>,
  })
  .event({
    schema: z.object({
      type: z.literal("sceneUpdated"),
      elements: z.array(z.record(z.string(), z.unknown())).optional(),
      appState: z.record(z.string(), z.unknown()).optional(),
      files: z.record(z.string(), z.unknown()).optional(),
    }),
    apply(state, event) {
      return {
        elements: event.elements ?? state.elements,
        appState: event.appState ?? state.appState,
        files: event.files ?? state.files,
      }
    },
  })
  .event({
    schema: z.object({
      type: z.literal("apiCalled"),
      path: z.string(),
      input: z.json(),
    }),
    apply(state, _event) {
      return state
    },
  })
  .event({
    schema: z.object({
      type: z.literal("uiEventLogged"),
      eventType: z.string(),
      data: z.json(),
    }),
    apply(state, _event) {
      return state
    },
  })
  .build()

export const apiModel = controlModel

export type ApiModel = typeof apiModel

export type ApiState = ApiModel["state"]

export interface Context {
  model: ApiModel
}

export const healthSchema = z.object({
  status: z.literal("ok"),
})

export const eventSchema = z.union(apiModel.eventsSchema)

export const dumpSchema = z.object({
  state: apiModel.stateSchema,
  events: eventSchema.array(),
})

export type Dump = z.infer<typeof dumpSchema>

export const seedInputSchema = z.object({
  events: eventSchema.array().optional(),
})

export type SeedInput = z.infer<typeof seedInputSchema>

export const streamEventSchema = z.union([
  z.object({
    type: z.literal("state"),
    state: apiModel.stateSchema,
  }),
])

export const controlRouter = {
  health: os.output(healthSchema).handler(async () => {
    return { status: "ok" }
  }),
  dump: os.output(dumpSchema).handler(async ({ context }) => {
    return {
      state: context.model.state,
      events: context.model.events,
    }
  }),
  seed: os
    .input(seedInputSchema)
    .output(dumpSchema)
    .handler(async ({ context, input }) => {
      context.model.reset(input.events)
      return {
        state: context.model.state,
        events: context.model.events,
      }
    }),
  stream: os.output(eventIterator(streamEventSchema)).handler(async function* ({ context, signal }) {
    const iterator = context.model.subscribe(signal)
    for await (const _event of iterator) {
      yield { type: "state", state: context.model.state }
    }
  }),
  getState: os.output(sceneStateSchema).handler(async ({ context }) => {
    return context.model.state
  }),
}

export const apiRouter = {
  _control: controlRouter,
}

export type ApiRouter = typeof apiRouter
