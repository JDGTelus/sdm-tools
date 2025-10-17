export default function TeamSprintDashboard() {
  return (
    <div className="min-h-screen">
      <div className="gradient-bg text-white py-12">
        <div className="container mx-auto px-6">
          <h1 className="text-4xl font-bold mb-4">Team Sprint Dashboard</h1>
          <p className="text-xl opacity-90">Sprint Analytics & Performance Insights</p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Coming Soon</h2>
          <p className="text-gray-600">
            This dashboard will show team sprint analytics including:
          </p>
          <ul className="list-disc list-inside mt-4 space-y-2 text-gray-600">
            <li>Sprint overview cards</li>
            <li>Developer performance metrics</li>
            <li>Sprint filtering and comparison</li>
            <li>Aggregated team statistics</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
