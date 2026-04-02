import { useState, useRef, useEffect } from 'react'

const EXAMPLES = [
  'Double J Stent 6FR 26cm Blue',
  'URETERAL CATHETER BLUE (OPEN END-PREMIUM) 04.0 FR 70 CM WITH HYDROPHILIC COATED',
  'AMPLATZ DILATOR 30FR 10CM',
  'Stone Basket 3FR 70cm',
  'Mono J Stent 6FR 20cm Green',
]

function ConfidenceBadge({ confidence }) {
  const map = {
    high:   { label: 'High',   color: '#22c55e', bg: 'rgba(34,197,94,0.12)' },
    medium: { label: 'Medium', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
    low:    { label: 'Low',    color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
  }
  const cfg = map[confidence] ?? map.low
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 12px', borderRadius: 99,
      background: cfg.bg, color: cfg.color,
      fontSize: 13, fontWeight: 600, letterSpacing: 0.3,
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: cfg.color, display: 'inline-block',
      }} />
      {cfg.label} Confidence
    </span>
  )
}

function MethodBadge({ method }) {
  return (
    <span style={{
      display: 'inline-block', padding: '4px 12px', borderRadius: 99,
      background: 'rgba(79,110,247,0.12)', color: '#4f6ef7',
      fontSize: 13, fontWeight: 600, letterSpacing: 0.3,
    }}>
      {method === 'constructed' ? 'Grammar-Constructed' : 'Fallback Match'}
    </span>
  )
}

function ResultCard({ result, index }) {
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(result.resolved_code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '20px 24px',
      animation: 'slideIn 0.25s ease',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.5, flex: 1 }}>
          {result.input_description}
        </p>
        <span style={{ color: 'var(--text-muted)', fontSize: 12, flexShrink: 0 }}>#{index + 1}</span>
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        background: 'var(--surface-2)', borderRadius: 8,
        padding: '12px 16px', marginBottom: 14,
      }}>
        <code style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 22, fontWeight: 700,
          color: result.resolved_code ? 'var(--text)' : 'var(--text-muted)',
          flex: 1, letterSpacing: 1.5,
        }}>
          {result.resolved_code || '—  No match found'}
        </code>
        {result.resolved_code && (
          <button onClick={copy} style={{
            background: copied ? 'rgba(34,197,94,0.15)' : 'var(--border)',
            border: 'none', borderRadius: 6, padding: '6px 12px',
            color: copied ? '#22c55e' : 'var(--text-muted)',
            fontSize: 12, fontWeight: 500, cursor: 'pointer',
            transition: 'all 0.15s',
          }}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <ConfidenceBadge confidence={result.confidence} />
        <MethodBadge method={result.method} />
      </div>
    </div>
  )
}

function HistoryItem({ item, onClick }) {
  return (
    <button onClick={() => onClick(item.input_description)} style={{
      width: '100%', textAlign: 'left', background: 'none',
      border: '1px solid var(--border)', borderRadius: 8,
      padding: '10px 12px', cursor: 'pointer',
      transition: 'background 0.15s',
    }}
    onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
    onMouseLeave={e => e.currentTarget.style.background = 'none'}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <code style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13, fontWeight: 700, color: 'var(--accent)',
          letterSpacing: 0.8,
        }}>
          {item.resolved_code || '—'}
        </code>
        <ConfidenceBadge confidence={item.confidence} />
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
        {item.input_description.length > 70
          ? item.input_description.slice(0, 67) + '...'
          : item.input_description}
      </p>
    </button>
  )
}

export default function App() {
  const [description, setDescription] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const textareaRef = useRef(null)

  useEffect(() => { textareaRef.current?.focus() }, [])

  const handleSubmit = async (e) => {
    e?.preventDefault()
    const text = description.trim()
    if (!text) return

    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: text }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Server error')
      }
      const data = await res.json()
      setResults(prev => [data, ...prev])
      setDescription('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit()
    }
  }

  const fillExample = (text) => {
    setDescription(text)
    textareaRef.current?.focus()
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        borderBottom: '1px solid var(--border)',
        padding: '16px 32px',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: 'var(--accent)', display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          fontSize: 18, fontWeight: 700, color: '#fff',
          flexShrink: 0,
        }}>M</div>
        <div>
          <h1 style={{ fontSize: 16, fontWeight: 700, letterSpacing: 0.3 }}>
            Marflow Product Code Resolver
          </h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 1 }}>
            Urology device description → standardized product code
          </p>
        </div>
      </header>

      {/* Main layout */}
      <div style={{
        flex: 1, display: 'grid',
        gridTemplateColumns: results.length ? '1fr 380px' : '1fr',
        gap: 0, maxWidth: 1400, width: '100%', margin: '0 auto',
        padding: 32, alignItems: 'start',
      }}>
        {/* Left: Input + Results */}
        <div style={{ paddingRight: results.length ? 32 : 0 }}>
          {/* Input */}
          <form onSubmit={handleSubmit}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, letterSpacing: 0.5 }}>
              PRODUCT DESCRIPTION
            </label>
            <textarea
              ref={textareaRef}
              value={description}
              onChange={e => setDescription(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. Double J Stent 6FR 26cm Blue..."
              rows={4}
              style={{
                width: '100%', background: 'var(--surface)',
                border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                color: 'var(--text)', fontSize: 15, fontFamily: 'Inter, sans-serif',
                padding: '14px 16px', resize: 'vertical', outline: 'none',
                transition: 'border-color 0.15s',
                lineHeight: 1.6,
              }}
              onFocus={e => e.target.style.borderColor = 'var(--accent)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Press <kbd style={{ background: 'var(--surface-2)', padding: '2px 6px', borderRadius: 4, fontSize: 11 }}>Ctrl+Enter</kbd> to resolve
              </p>
              <button
                type="submit"
                disabled={loading || !description.trim()}
                style={{
                  background: loading || !description.trim() ? 'var(--surface-2)' : 'var(--accent)',
                  color: loading || !description.trim() ? 'var(--text-muted)' : '#fff',
                  border: 'none', borderRadius: 8,
                  padding: '10px 28px', fontSize: 14, fontWeight: 600,
                  cursor: loading || !description.trim() ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s', letterSpacing: 0.3,
                }}
              >
                {loading ? 'Resolving...' : 'Resolve Code'}
              </button>
            </div>
          </form>

          {/* Error */}
          {error && (
            <div style={{
              marginTop: 16, padding: '12px 16px',
              background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 8, color: '#ef4444', fontSize: 14,
            }}>
              {error}
            </div>
          )}

          {/* Examples */}
          {results.length === 0 && !error && (
            <div style={{ marginTop: 32 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 0.5, marginBottom: 12 }}>
                TRY AN EXAMPLE
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {EXAMPLES.map((ex, i) => (
                  <button key={i} onClick={() => fillExample(ex)} style={{
                    textAlign: 'left', background: 'var(--surface)',
                    border: '1px solid var(--border)', borderRadius: 8,
                    padding: '10px 14px', cursor: 'pointer', color: 'var(--text)',
                    fontSize: 13, transition: 'border-color 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {results.length > 0 && (
            <div style={{ marginTop: 28 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 0.5, marginBottom: 12 }}>
                RESULTS
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {results.map((r, i) => (
                  <ResultCard key={i} result={r} index={i} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: History sidebar */}
        {results.length > 0 && (
          <div style={{
            borderLeft: '1px solid var(--border)',
            paddingLeft: 32, position: 'sticky', top: 32,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 0.5 }}>
                HISTORY ({results.length})
              </p>
              <button onClick={() => setResults([])} style={{
                background: 'none', border: 'none', color: 'var(--text-muted)',
                fontSize: 12, cursor: 'pointer', padding: '2px 6px',
                borderRadius: 4, transition: 'color 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
              >
                Clear all
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {results.map((r, i) => (
                <HistoryItem key={i} item={r} onClick={fillExample} />
              ))}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
