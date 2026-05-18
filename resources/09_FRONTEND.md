# Frontend (`App.tsx`)

## Tech stack

- **Framework:** React 18 + TypeScript
- **Build:** Vite
- **Markdown:** react-markdown + remark-gfm
- **HTTP:** fetch with ReadableStream for SSE

## Core components

### Chat UI (App.tsx)

The app renders a single chat interface with:

```
┌─────────────────────────────────┐
│  FinDoc AI              [Model] │  ← header + model dropdown
├─────────────────────────────────┤
│  User message (markdown)        │
│  AI response (markdown)         │
│    [batch1-0494.jpg]            │  ← file chips
│  User message ...               │
│  AI response ...                │
│    [batch1-0188.jpg]            │
├─────────────────────────────────┤
│  [Type a message...]    [Send]  │  ← input
└─────────────────────────────────┘
```

### SSE Parsing

The frontend reads the server's SSE stream using the Fetch API with `ReadableStream`:

```typescript
// Simplified from App.tsx
const response = await fetch("/api/chat", { method: "POST", body: ... });
const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    const text = decoder.decode(value);
    for (const line of text.split("\n")) {
        if (line.startsWith("data: __files__")) {
            const files = JSON.parse(line.slice(15));  // skip "data: __files__"
            // Store files for the next assistant message
        } else if (line.startsWith("data: ")) {
            const chunk = line.slice(6);               // skip "data: "
            // Append to current assistant message text
        }
    }
}
```

Key detail: `line.slice(15)` to strip `data: __files__` prefix (15 chars), and `line.slice(6)` to strip `data: ` prefix (6 chars).

### Markdown Rendering

Uses `react-markdown` with `remark-gfm` for GitHub-Flavored Markdown:

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

<ReactMarkdown remarkPlugins={[remarkGfm]}>
    {message}
</ReactMarkdown>
```

Custom `.markdown-body` CSS in `index.css` ensures light-mode readability using the app's theme variables (replacing the default Tailwind `prose` class which had contrast issues).

### File Chips

Retrieved files appear as clickable chips below the assistant's answer:

```tsx
{message.files?.map((file) => (
    <a key={file.id} href={file.url} target="_blank" className="file-chip">
        {file.name}
    </a>
))}
```

File URLs point to the backend (`/api/files/batch1-0494.jpg`) which serves the JPEG images.

### Model Toggle

A dropdown in the header lets users switch between Auto, Gemini, and Local:

```tsx
<select value={model} onChange={(e) => setModel(e.target.value)}>
    <option value="auto">Auto</option>
    <option value="gemini">Gemini</option>
    <option value="local">Local</option>
</select>
```

The selected model is sent with every chat request in `ChatRequest.model`.

## Development

```bash
npm run dev    # Vite dev server on port 3000
```

The frontend proxies `/api/*` requests to the backend (configured in `vite.config.ts` or via `BACKEND_URL`).

## Related files

| File | Role |
|---|---|
| `frontend/src/App.tsx` | Main chat component, SSE parsing, file rendering |
| `frontend/src/index.css` | `.markdown-body` custom styles |
| `frontend/package.json` | Dependencies (react-markdown, remark-gfm) |
