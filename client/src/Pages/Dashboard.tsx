import { FormEvent, useEffect, useMemo, useState } from "react"
import { supabase } from "../lib/supabase"

type SearchSource = {
  title?: string
  url?: string
  content?: string
  score?: number
}

type AskResponse = {
  answer?: string
  llm_response?: string
  search_result?: {
    query?: string
    results?: SearchSource[]
  }
}

const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"
const RECENT_KEY = "pp_recent_chats"

const suggestions = [
  "What is the fastest way to learn React?",
  "Explain JWT authentication simply",
  "How do I make a SaaS landing page convert?",
  "Compare FastAPI vs Express",
]

const readRecentChats = (): string[] => {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]") as string[]
  } catch {
    return []
  }
}

const Dashboard = () => {
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [sources, setSources] = useState<SearchSource[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [recentChats, setRecentChats] = useState<string[]>([])

  useEffect(() => {
    setRecentChats(readRecentChats())
  }, [])

  const saveRecent = (item: string) => {
    const next = [item, ...recentChats.filter((value) => value !== item)].slice(0, 8)
    setRecentChats(next)
    localStorage.setItem(RECENT_KEY, JSON.stringify(next))
  }

  const askQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const prompt = question.trim()

    if (!prompt) {
      return
    }

    setLoading(true)
    setError("")
    setAnswer("")
    setSources([])

    try {
      const sessionResp = await supabase.auth.getSession()
      const token = sessionResp.data?.session?.access_token

      const response = await fetch(`${API_BASE}/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ question: prompt }),
      })

      if (!response.ok) {
        const err = await response.text()
        throw new Error(err || "Unable to fetch answer")
      }

      // Parse SSE stream
      const reader = response.body?.getReader()
      if (!reader) throw new Error("Response body is empty")

      const decoder = new TextDecoder()
      let buffer = ""
      let currentAnswer = ""

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")

        // Keep incomplete line in buffer
        buffer = lines[lines.length - 1]

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim()
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6)
            try {
              const event = JSON.parse(jsonStr)

              if (event.type === "search_result" && event.data) {
                // Update sources from search result
                const searchData = event.data
                if (searchData.results) {
                  setSources(searchData.results)
                }
              } else if (event.type === "chunk" && event.data) {
                // Accumulate and display text chunks in real-time
                currentAnswer += event.data
                setAnswer(currentAnswer)
              } else if (event.type === "done") {
                // Stream complete
                saveRecent(prompt)
              } else if (event.type === "error") {
                throw new Error(event.error || "Stream error")
              }
            } catch (parseErr) {
              console.error("Failed to parse SSE event:", jsonStr, parseErr)
            }
          }
        }
      }

      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
      setLoading(false)
    }
  }

  return (
    <div className="dashboard">
      <section className="hero">
        <p className="eyebrow">Ask anything</p>
        <h1>Search with answers, not just links.</h1>
        <p className="hero__sub">
          A Perplexity-like experience for your AI search app.
        </p>

        <form className="composer" onSubmit={askQuestion}>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What do you want to know?"
            rows={4}
          />

          <div className="composer__row">
            <div className="composer__chips">
              {suggestions.map((item) => (
                <button
                  type="button"
                  key={item}
                  className="chip"
                  onClick={() => setQuestion(item)}
                >
                  {item}
                </button>
              ))}
            </div>

            <button type="submit" className="ask-button" disabled={loading}>
              {loading ? "Searching..." : "Ask"}
            </button>
          </div>
        </form>
      </section>

      {error ? <div className="alert">{error}</div> : null}

      <section className="grid">
        <article className="panel panel--answer">
          <div className="panel__head">
            <span>Answer</span>
            <span>{loading ? "Working..." : "Ready"}</span>
          </div>

          <div className="answer">
            {answer ? answer : "Your answer will appear here after you ask a question."}
          </div>
        </article>

        <aside className="panel panel--sources">
          <div className="panel__head">
            <span>Sources</span>
            <span>{sources.length}</span>
          </div>

          {sources.length > 0 ? (
            <div className="sources">
              {sources.map((source, index) => (
                <a
                  key={`${source.url ?? index}`}
                  className="source"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <div className="source__index">{index + 1}</div>
                  <div className="source__body">
                    <div className="source__title">{source.title ?? source.url}</div>
                    <div className="source__content">
                      {source.content ?? "Open source"}
                    </div>
                    <div className="source__meta">
                      {source.score ? `Score ${source.score.toFixed(2)}` : "Source"}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              Sources will show here once results are returned.
            </div>
          )}
        </aside>
      </section>

      <section className="panel panel--history">
        <div className="panel__head">
          <span>Recent searches</span>
          <span>{recentChats.length}</span>
        </div>

        {recentChats.length > 0 ? (
          <div className="history-list">
            {recentChats.map((item) => (
              <button
                key={item}
                type="button"
                className="history-item"
                onClick={() => setQuestion(item)}
              >
                {item}
              </button>
            ))}
          </div>
        ) : (
          <div className="empty-state">No recent chats yet.</div>
        )}
      </section>
    </div>
  )
}

export default Dashboard