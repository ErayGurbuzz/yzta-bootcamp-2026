import QuizResult from './QuizResult.jsx'

export default function QuizPanel({
  quiz,
  quizAnswers,
  setQuizAnswers,
  quizResult,
  onGenerate,
  onSubmit,
  loading,
  selectedDoc,
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Quiz Engine</h2>
        <button onClick={onGenerate} className="btn" disabled={loading || !selectedDoc}>5 Soruluk Quiz Oluştur</button>
      </div>
      {quiz && (
        <div className="mt-5 space-y-4">
          {quiz.questions.map((q, idx) => (
            <div key={q.id} className="rounded-2xl border border-slate-800 p-4">
              <p className="font-semibold">{idx + 1}. {q.question_text}</p>
              <p className="mt-1 text-xs text-slate-400">Konu: {q.topic} • Kaynak Sayfa: {q.source_page ?? '-'}</p>
              <div className="mt-3 space-y-2">
                {q.options.map((opt) => (
                  <label key={opt} className="flex cursor-pointer gap-2 rounded-xl border border-slate-800 p-2 hover:bg-slate-800">
                    <input type="radio" name={`q-${q.id}`} value={opt} onChange={() => setQuizAnswers({ ...quizAnswers, [q.id]: opt })} />
                    <span>{opt}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}
          <button onClick={onSubmit} className="btn w-full" disabled={loading}>Quiz'i Bitir</button>
        </div>
      )}
      <QuizResult quizResult={quizResult} />
    </div>
  )
}
