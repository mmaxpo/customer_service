export interface CapabilityState<T> {
  data: T;

  status:
    | "idle"
    | "loading"
    | "ready"
    | "refreshing"
    | "error";

  error: string | null;

  refresh(): Promise<void>;
}
