import { redirect } from "next/navigation";

// The chatbot page moved into Settings → Chat widget.
export default function ChatbotPage() {
  redirect("/app/settings/chat-widget");
}
