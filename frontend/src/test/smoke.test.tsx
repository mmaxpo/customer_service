import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

function Smoke() {
    return <div>Tajeran UI ready</div>;
}

describe("frontend smoke", () => {
    it("renders", () => {
        render(<Smoke />);
        expect(screen.getByText("Tajeran UI ready")).toBeInTheDocument();
    });
});