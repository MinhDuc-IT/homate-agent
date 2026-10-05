type LoadingListener = (pendingCount: number) => void

let pendingCount = 0
const listeners = new Set<LoadingListener>()

function notify() {
  listeners.forEach((listener) => listener(pendingCount))
}

export function getPendingRequestCount() {
  return pendingCount
}

export function subscribeLoading(listener: LoadingListener) {
  listeners.add(listener)
  listener(pendingCount)
  return () => {
    listeners.delete(listener)
  }
}

export function trackLoading<T>(promise: Promise<T>): Promise<T> {
  pendingCount += 1
  notify()

  return promise.finally(() => {
    pendingCount = Math.max(0, pendingCount - 1)
    notify()
  })
}
