type Subscriber<T> = (value: T) => void

export class Emitter<T> {
  private subscribers = new Set<Subscriber<T>>()

  emit(value: T) {
    for (const subscriber of this.subscribers) {
      subscriber(value)
    }
  }

  subscribe(signal?: AbortSignal): AsyncIterableIterator<T> {
    let done = false

    const queue: T[] = []
    const waiters: ((r: IteratorResult<T>) => void)[] = []

    const push = (value: T) => {
      if (done) return

      const waiter = waiters.shift()
      if (waiter) {
        waiter({ value, done: false })
      } else {
        queue.push(value)
      }
    }

    // Register as a normal subscriber
    this.subscribers.add(push)

    const cleanup = () => {
      if (done) return
      done = true

      this.subscribers.delete(push)

      // Resolve any pending next() calls so iteration ends promptly
      for (const waiter of waiters.splice(0)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        waiter({ value: undefined as any, done: true })
      }
    }

    if (signal) {
      if (signal.aborted) cleanup()
      else signal.addEventListener("abort", cleanup, { once: true })
    }

    const iterator: AsyncIterableIterator<T> = {
      [Symbol.asyncIterator]() {
        return this
      },

      next(): Promise<IteratorResult<T>> {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (done) return Promise.resolve({ value: undefined as any, done: true })

        const value = queue.shift()
        if (value !== undefined) {
          return Promise.resolve({ value, done: false })
        }

        return new Promise<IteratorResult<T>>(resolve => {
          waiters.push(resolve)
        })
      },

      // Called if consumer breaks early (e.g. `break`, `return`)
      return(): Promise<IteratorResult<T>> {
        cleanup()
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return Promise.resolve({ value: undefined as any, done: true })
      },

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      throw(err?: any): Promise<IteratorResult<T>> {
        cleanup()
        return Promise.reject(err)
      },
    }

    return iterator
  }
}
