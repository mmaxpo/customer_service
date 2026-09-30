type Callback = (event: MessageEvent) => void;

export class EventSourceClient {
  private source: EventSource | null = null;

  connect(url: string, onMessage: Callback) {
    this.disconnect();

    this.source = new EventSource(url);

    this.source.onmessage = onMessage;

    this.source.onerror = () => {
      console.warn("Realtime disconnected");
    };
  }

  disconnect() {
    this.source?.close();
    this.source = null;
  }
}

export const realtimeClient =
  new EventSourceClient();
