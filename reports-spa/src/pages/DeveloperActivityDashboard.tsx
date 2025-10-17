export default function DeveloperActivityDashboard() {
  return (
    <div className="min-h-screen">
      <div className="gradient-bg text-white py-12">
        <div className="container mx-auto px-6">
          <h1 className="text-4xl font-bold mb-4">Developer Activity Dashboard</h1>
          <p className="text-xl opacity-90">Individual Activity Tracking & Analysis</p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Coming Soon</h2>
          <p className="text-gray-600">
            This dashboard will show developer activity including:
          </p>
          <ul className="list-disc list-inside mt-4 space-y-2 text-gray-600">
            <li>Sprint-based activity breakdown</li>
            <li>Last 3 days activity tracking</li>
            <li>Jira vs Repo actions charts</li>
            <li>Activity distribution pie charts</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
