export default function DocumentUpload({ courses, selectedCourse, setSelectedCourse, setFile, onSubmit, loading, file }) {
  return (
    <div className="card">
      <h2 className="text-xl font-bold">2. PDF Yükle</h2>
      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <select className="input" value={selectedCourse} onChange={(e) => setSelectedCourse(e.target.value)}>
          <option value="">Ders seç</option>
          {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
        </select>
        <input className="input" type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0])} />
        <button className="btn w-full" disabled={loading || !selectedCourse || !file}>PDF Yükle ve İşle</button>
      </form>
    </div>
  )
}
