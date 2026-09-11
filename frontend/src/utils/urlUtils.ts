/**
 * Client-side URL parsing utility — mirrors the backend url_validator logic
 * so the UI can show a preview without a round-trip.
 */
export function parse_pasted_urls_client(text: string): string[] {
  if (!text.trim()) return []
  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n')
  const urls: string[] = []
  for (const line of lines) {
    const parts = line.split(',')
    for (const part of parts) {
      const stripped = part.trim()
      if (stripped) urls.push(stripped)
    }
  }
  return urls
}
