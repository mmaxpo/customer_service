export function extractOrderRef(text: string) {
  const patterns = [
    /#\d{3,}/,
    /order\s*#?\s*([a-zA-Z0-9-]{3,})/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) continue;
    return (match[1] ?? match[0]).replace(/^order\s*/i, "").trim();
  }

  return null;
}
