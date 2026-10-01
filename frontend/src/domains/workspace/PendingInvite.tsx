"use client";

import { useEffect } from "react";

/** After someone signs in, finish an invitation they started before signing up. */
export function PendingInvite() {
  useEffect(() => {
    try {
      const token = localStorage.getItem("tajeran-invite-token");
      if (token) window.location.replace(`/invite/accept?token=${encodeURIComponent(token)}`);
    } catch {
      // No browser storage: the invite link in the email still works.
    }
  }, []);
  return null;
}
