export type EventHandler<T = unknown> =
  (payload: T) => void;

export interface FrontendEvent<T = unknown> {
  type: string;
  payload: T;
}
