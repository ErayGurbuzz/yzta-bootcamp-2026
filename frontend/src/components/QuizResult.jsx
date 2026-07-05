export default function QuizResult({ quizResult }) {
  if (!quizResult) return null

  return (
    <div className="mt-6 rounded-2xl border border-indigo-800 bg-indigo-950/30 p-4">
      <h3 className="text-lg font-bold">Sonuç: {quizResult.score}/{quizResult.total_questions} • %{quizResult.percentage}</h3>
      <p className="mt-2 text-yellow-200">En zayıf konu: {quizResult.weak_topic || 'Yok'}</p>
      <p className="mt-1 text-slate-200">{quizResult.recommendation}</p>
      <div className="mt-4 space-y-3">
        {quizResult.answers.map((a) => (
          <div key={a.question_id} className="rounded-xl border border-slate-800 p-3 text-sm">
            <p className={a.is_correct ? 'text-emerald-300' : 'text-red-300'}>{a.is_correct ? 'Doğru' : 'Yanlış'} • Senin cevabın: {a.user_answer}</p>
            <p>Doğru cevap: {a.correct_answer}</p>
            <p className="text-slate-300">Açıklama: {a.explanation}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
