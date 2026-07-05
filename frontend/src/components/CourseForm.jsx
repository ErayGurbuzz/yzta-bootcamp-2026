export default function CourseForm({ courseTitle, setCourseTitle, onSubmit, loading }) {
  return (
    <div className="card">
      <h2 className="text-xl font-bold">1. Ders Oluştur</h2>
      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <input className="input" value={courseTitle} onChange={(e) => setCourseTitle(e.target.value)} />
        <button className="btn w-full" disabled={loading}>Ders Oluştur</button>
      </form>
    </div>
  )
}
