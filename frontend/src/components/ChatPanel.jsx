export default function ChatPanel({
  question,
  setQuestion,
  mode,
  setMode,
  onSubmit,
  loading,
  selectedDoc,
  chatResult,
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold">RAG Chat + Citation</h2>
        <select className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm" value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="default">Normal</option>
          <option value="simple">Basit anlat</option>
          <option value="examples">Örnek ver</option>
        </select>
      </div>
      <form onSubmit={onSubmit} className="mt-4 flex gap-3">
        <input className="input" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button className="btn" disabled={loading || !selectedDoc}>Sor</button>
      </form>
      {chatResult && (
        <div className="mt-5 rounded-2xl bg-slate-950 p-4">
          <p className="whitespace-pre-wrap text-slate-100">{chatResult.answer}</p>
          <div className="mt-4 border-t border-slate-800 pt-3">
            <p className="text-sm font-semibold text-slate-300">Kaynaklar</p>
            <div className="mt-2 grid gap-2">
              {chatResult.sources.map((src) => (
                <div key={src.chunk_id} className="rounded-xl border border-slate-800 p-3 text-xs text-slate-300">
                  Doküman {src.document_id}, Sayfa {src.page}: {src.text_preview}...
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
