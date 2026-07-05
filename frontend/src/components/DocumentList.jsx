export default function DocumentList({ documents, readyDocuments, selectedDoc, setSelectedDoc }) {
  return (
    <div className="card">
      <h2 className="text-xl font-bold">Dokümanlar</h2>
      <select className="input mt-4" value={selectedDoc} onChange={(e) => setSelectedDoc(e.target.value)}>
        <option value="">Hazır doküman seç</option>
        {readyDocuments.map((doc) => <option key={doc.id} value={doc.id}>{doc.original_filename}</option>)}
      </select>
      <div className="mt-4 space-y-2">
        {documents.map((doc) => (
          <div key={doc.id} className="rounded-xl border border-slate-800 p-3 text-sm">
            <div className="font-medium">{doc.original_filename}</div>
            <div className={doc.status === 'ready' ? 'text-emerald-300' : doc.status === 'failed' ? 'text-red-300' : 'text-yellow-300'}>
              {doc.status} • {doc.page_count} sayfa
            </div>
            {doc.error_message && <div className="mt-1 text-red-300">{doc.error_message}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
