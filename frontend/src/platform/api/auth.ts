import { apiFetch, apiJson, jsonBody } from "./client";

export const authApi = {
    signup(payload: {
        email: string;
        password: string;
        full_name?: string;
        terms_accepted: true;
        terms_version: string;
        privacy_accepted: true;
        privacy_version: string;
    }) {
        return apiJson("/api/auth/signup", {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    login(payload: { email: string; password: string }) {
        return apiJson("/api/auth/login", {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    requestPasswordReset(email: string) {
        return apiJson("/api/auth/password-reset/request", {
            method: "POST",
            body: jsonBody({ email }),
        });
    },

    confirmPasswordReset(token: string, new_password: string) {
        return apiJson("/api/auth/password-reset/confirm", {
            method: "POST",
            body: jsonBody({ token, new_password }),
        });
    },

    // Ends the session, then always leaves the app: a failed call must not
    // strand someone on a screen they believe they have left.
    async logout() {
        try {
            await apiFetch("/api/auth/logout", { method: "POST" });
        } finally {
            window.location.href = "/login";
        }
    },

    me() {
        return apiJson("/api/auth/me");
    },

    requestEmailVerification() {
        return apiJson("/api/auth/email-verification/request", {
            method: "POST",
        });
    },

    confirmEmailVerification(token: string) {
        return apiJson("/api/auth/email-verification/confirm", {
            method: "POST",
            body: jsonBody({ token }),
        });
    },
};
