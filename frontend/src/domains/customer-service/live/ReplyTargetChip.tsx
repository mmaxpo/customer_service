import { ToneChip } from "../inbox/case/parts";
import type { WaitingConversation } from "./api";

/** Shown on a waiting conversation that is close to, or past, the reply target. */
export function ReplyTargetChip({ item }: { item: Pick<WaitingConversation, "reply_due_at" | "target_state"> }) {
  if (item.target_state === "missed") return <ToneChip tone="failure">Reply target missed</ToneChip>;
  if (item.target_state !== "close" || !item.reply_due_at) return null;

  const minutes = Math.max(1, Math.round((new Date(item.reply_due_at).getTime() - Date.now()) / 60000));
  const left = minutes < 60 ? `${minutes} min` : `${Math.round(minutes / 6) / 10} hrs`;
  return <ToneChip tone="attention">Reply due in {left}</ToneChip>;
}
