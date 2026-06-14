import { z } from "zod"

import { Emitter } from "./_emitter.js"

export interface ModelBuilder {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  state<TState>(def: StateDefinition<TState>): StateBuilder<TState, {}>
}

export interface StateBuilder<TState, TEventDefinitions extends AnyEventDefinitions<TState>> {
  state: StateDefinition<TState>
  events: TEventDefinitions

  event<TEvent extends AnyEvent>(
    def: EventDefinition<TState, TEvent>
  ): StateBuilder<TState, Expand<TEventDefinitions & Record<TEvent["type"], EventDefinition<TState, TEvent>>>>

  build(): Model<TState, TEventDefinitions>
}

export interface StateDefinition<TState> {
  schema: z.core.$ZodType<TState>
  initial: TState
}

export interface AnyEvent {
  type: string
}

export interface EventDefinition<TState, TEvent extends AnyEvent> {
  schema: z.core.$ZodType<TEvent>
  apply(state: TState, event: TEvent): TState
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AnyEventDefinitions<TState = any> = Record<string, EventDefinition<TState, any>>

export const model: ModelBuilder = {
  state<TState>(def: StateDefinition<TState>) {
    return new StateBuilderImpl(def, {})
  },
}

class StateBuilderImpl<TState, TEventDefinitions extends AnyEventDefinitions<TState>> implements StateBuilder<
  TState,
  TEventDefinitions
> {
  constructor(
    public state: StateDefinition<TState>,
    public events: TEventDefinitions
  ) {}

  event<TEvent extends AnyEvent>(
    def: EventDefinition<TState, TEvent>
  ): StateBuilder<TState, Expand<TEventDefinitions & Record<TEvent["type"], EventDefinition<TState, TEvent>>>> {
    // This should be safe
    const key = (def.schema._zod.def as z.ZodObject["def"]).shape["type"].def.values[0]
    return new StateBuilderImpl(this.state, { ...this.events, [key]: def } as unknown as Expand<
      TEventDefinitions & Record<TEvent["type"], EventDefinition<TState, TEvent>>
    >)
  }

  build(): Model<TState, TEventDefinitions> {
    return new ModelImpl(this.state, this.events)
  }
}

export interface Model<TState, TEventDefinitions extends AnyEventDefinitions<TState>> {
  readonly stateSchema: z.core.$ZodType<TState>
  readonly eventsSchema: z.core.$ZodType<Expand<AnyEventIn<TEventDefinitions>>>[]

  readonly state: TState
  readonly events: AnyEventIn<TEventDefinitions>[]

  reset(events?: AnyEventIn<TEventDefinitions>[]): TState
  apply<TEvent extends AnyEventIn<TEventDefinitions>>(event: TEvent): TState
  subscribe(signal?: AbortSignal): AsyncIterable<AnyEventIn<TEventDefinitions>>
}

export type Expand<T> = T extends infer O ? { [K in keyof O]: O[K] } : never

export type AnyEventIn<TEventDefinitions extends AnyEventDefinitions> = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [K in keyof TEventDefinitions]: TEventDefinitions[K] extends EventDefinition<any, infer TEvent> ? TEvent : never
}[keyof TEventDefinitions]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AnyModel = Model<any, any>

export class ModelImpl<TState, TEventDefinitions extends AnyEventDefinitions<TState>> implements Model<
  TState,
  TEventDefinitions
> {
  readonly stateSchema: z.core.$ZodType<TState>
  readonly eventsSchema: z.core.$ZodType<Expand<AnyEventIn<TEventDefinitions>>>[]

  state: TState
  events: AnyEventIn<TEventDefinitions>[]

  private emitter: Emitter<AnyEventIn<TEventDefinitions>>

  constructor(
    readonly stateDef: StateDefinition<TState>,
    readonly eventDefs: TEventDefinitions
  ) {
    this.stateSchema = this.stateDef.schema
    this.eventsSchema = Object.values(eventDefs).map(def => def.schema)

    this.state = this.stateDef.initial
    this.events = []

    this.emitter = new Emitter<AnyEventIn<TEventDefinitions>>()
  }

  reset(events: AnyEventIn<TEventDefinitions>[] = []): TState {
    this.state = this.stateDef.initial
    this.events = []

    for (const event of events) {
      this.apply(event)
    }

    return this.state
  }

  apply<TEvent extends AnyEventIn<TEventDefinitions>>(event: TEvent): TState {
    const eventDef = this.eventDefs[event.type]
    if (eventDef) {
      this.events.push(event)
      this.state = eventDef.apply(this.state, event)

      this.emitter.emit(event)
    }

    return this.state
  }

  subscribe(signal?: AbortSignal): AsyncIterable<AnyEventIn<TEventDefinitions>> {
    return this.emitter.subscribe(signal)
  }
}

export type ModelsState<TModels extends Record<string, AnyModel>> = Expand<{
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [K in keyof TModels]: TModels[K] extends Model<infer TState, any> ? TState : never
}>

export type ModelsEventDefinitions<TModels extends Record<string, AnyModel>> = Expand<
  {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [K in keyof TModels]: TModels[K] extends Model<any, infer TEventDefinitions>
      ? (_: TEventDefinitions) => void
      : never
  }[keyof TModels] extends (_: infer U) => void
    ? U
    : never
>

export function models<TModels extends Record<string, AnyModel>>(
  defs: TModels
): Model<ModelsState<TModels>, ModelsEventDefinitions<TModels>> {
  return new ModelsImpl(defs)
}

export class ModelsImpl<TModels extends Record<string, AnyModel>> implements Model<
  ModelsState<TModels>,
  ModelsEventDefinitions<TModels>
> {
  readonly stateSchema: z.core.$ZodType<ModelsState<TModels>>
  readonly eventsSchema: z.core.$ZodType<Expand<AnyEventIn<ModelsEventDefinitions<TModels>>>>[]

  state: ModelsState<TModels>
  events: AnyEventIn<ModelsEventDefinitions<TModels>>[]

  private emitter: Emitter<AnyEventIn<ModelsEventDefinitions<TModels>>>

  constructor(private readonly models: TModels) {
    this.stateSchema = z.object(
      Object.fromEntries(Object.entries(models).map(([key, model]) => [key, model.stateSchema]))
    ) as unknown as z.core.$ZodType<ModelsState<TModels>>
    this.eventsSchema = Object.values(models).flatMap(model => model.eventsSchema) as unknown as z.core.$ZodType<
      Expand<AnyEventIn<ModelsEventDefinitions<TModels>>>
    >[]

    this.state = Object.fromEntries(
      Object.entries(models).map(([key, model]) => [key, model.state])
    ) as ModelsState<TModels>
    this.events = []

    this.emitter = new Emitter<AnyEventIn<ModelsEventDefinitions<TModels>>>()
  }

  reset(events: AnyEventIn<ModelsEventDefinitions<TModels>>[] = []): ModelsState<TModels> {
    for (const [key, model] of Object.entries(this.models)) {
      this.state[key as keyof ModelsState<TModels>] = model.reset()
    }

    this.events = []
    for (const event of events) {
      this.apply(event)
    }

    return this.state
  }

  apply<TEvent extends AnyEventIn<ModelsEventDefinitions<TModels>>>(event: TEvent): ModelsState<TModels> {
    this.state = Object.fromEntries(
      Object.entries(this.models).map(([key, model]) => [key, model.apply(event)])
    ) as ModelsState<TModels>

    this.events.push(event)
    this.emitter.emit(event)

    return this.state
  }

  subscribe(signal?: AbortSignal): AsyncIterable<AnyEventIn<ModelsEventDefinitions<TModels>>> {
    return this.emitter.subscribe(signal)
  }
}
