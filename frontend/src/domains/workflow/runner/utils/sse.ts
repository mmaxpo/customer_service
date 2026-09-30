export function parseSseFrames(buffer: string) {
    // frames separated by blank line
    return buffer.split("\n\n").map((x) => x.trim()).filter(Boolean);
}

export function extractDataJson(frame: string): string | null {
    // prefer "data:" line
    const lines = frame.split("\n");
    const dataLine = lines.find((l) => l.startsWith("data:"));
    if (!dataLine) return null;
    return dataLine.slice(5).trim();
}