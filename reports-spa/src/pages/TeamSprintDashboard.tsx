import { useEffect, useState } from 'react'
import { getSprintData, isDataAvailable } from '@/data/embeddedData'
import type { TeamSprintData } from '@/data/types'

export default function TeamSprintDashboard() {
  const [sprintData, setSprintData] = useState<TeamSprintData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Access embedded data
    const data = getSprintData()
    setSprintData(data)
    setLoading(false)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-telus-purple"></div>
      </div>
    )
  }

  const sprintCount = sprintData ? Object.keys(sprintData.sprint_analytics).length : 0
  const dataAvailable = isDataAvailable()

  return (
    <div className="min-h-screen">
      <div className="gradient-bg text-white py-12">
        <div className="container mx-auto px-6">
          <h1 className="text-4xl font-bold mb-4">Team Sprint Dashboard</h1>
          <p className="text-xl opacity-90">Sprint Analytics & Performance Insights</p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Data Status Card */}
        <div className={`rounded-xl shadow-lg p-6 mb-8 ${dataAvailable ? 'bg-green-50 border-2 border-green-200' : 'bg-yellow-50 border-2 border-yellow-200'}`}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">
                {dataAvailable ? '✓ Data Loaded Successfully' : '⚠ Data Not Available'}
              </h2>
              <p className="text-gray-600">
                {dataAvailable 
                  ? `Embedded data contains ${sprintCount} sprints`
                  : 'Run build with data files present to embed data'
                }
              </p>
            </div>
            {sprintData && (
              <div className="text-right">
                <p className="text-sm text-gray-500">Generated</p>
                <p className="text-sm font-semibold text-gray-700">
                  {new Date(sprintData.generated_at).toLocaleDateString()}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Info Card */}
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Dashboard Features</h2>
          <p className="text-gray-600 mb-4">
            This dashboard will show team sprint analytics including:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-600">
            <li>Sprint overview cards</li>
            <li>Developer performance metrics</li>
            <li>Sprint filtering and comparison</li>
            <li>Aggregated team statistics</li>
          </ul>

          {sprintData && (
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold text-blue-900 mb-2">Available Sprints:</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {Object.values(sprintData.sprint_analytics).slice(0, 6).map((sprint) => (
                  <div key={sprint.sprint_info.id} className="text-sm text-blue-700">
                    • {sprint.sprint_info.name}
                  </div>
                ))}
                {sprintCount > 6 && (
                  <div className="text-sm text-blue-700">
                    ... and {sprintCount - 6} more
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
