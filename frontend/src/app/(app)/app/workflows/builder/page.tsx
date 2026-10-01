import { redirect } from "next/navigation";

// New workflows are now drafted from the Ask TCOS bar on the Workflows page.
export default function Page() {
  redirect("/app/workflows");
}
