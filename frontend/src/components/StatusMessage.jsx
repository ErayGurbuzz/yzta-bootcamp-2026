export default function StatusMessage({ message, error }) {
  if (!message && !error) return null

  const className = error
    ? 'rounded-xl border border-red-900 bg-red-950/60 p-4 text-red-200'
    : 'rounded-xl border border-emerald-900 bg-emerald-950/40 p-4 text-emerald-200'

  return <div className={className}>{error || message}</div>
}
