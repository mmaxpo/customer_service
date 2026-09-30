import type {
  EventHandler,
  FrontendEvent,
} from "./types";

class EventBus {
  private handlers = new Map<string, Set<EventHandler>>();
  private observers = new Set<EventHandler<FrontendEvent>>();

  publish<T>(event: FrontendEvent<T>) {
    this.observers.forEach((observer) => {
      observer(event as FrontendEvent);
    });

    const listeners = this.handlers.get(event.type);
    if (!listeners) return;

    listeners.forEach((listener) => {
      listener(event.payload);
    });
  }

  subscribe<T>(type: string, handler: EventHandler<T>) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }

    this.handlers.get(type)!.add(handler as EventHandler);

    return () => {
      this.handlers.get(type)?.delete(handler as EventHandler);
    };
  }

  observe(handler: EventHandler<FrontendEvent>) {
    this.observers.add(handler);

    return () => {
      this.observers.delete(handler);
    };
  }
}

export const eventBus = new EventBus();
