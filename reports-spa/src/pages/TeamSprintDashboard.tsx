import { useEffect, useState, useMemo } from 'react'
import { getSprintData, isDataAvailable } from '@/data/embeddedData'
import type { TeamSprintData } from '@/data/types'
import { MetricCard, SummaryCard } from '@/components/shared'
import { BarChart, PieChart, RadarChart } from '@/components/charts'

export default function TeamSprintDashboard() {
  const [sprintData, setSprintData] = useState<TeamSprintData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const data = getSprintData()
    setSprintData(data)
    setLoading(false)
  }, [])

  const stats = useMemo(() => {
    if (!sprintData) return null

    const sprints = Object.values(sprintData.sprint_analytics)
    const totalDevelopers = new Set<string>()
    let totalCommits = 0
    let totalIssues = 0
    let totalStoryPoints = 0

    sprints.forEach(sprint => {
      Object.values(sprint.developers).forEach(dev => {
        totalDevelopers.add(dev.email)
        totalCommits += dev.commits_in_sprint
        totalIssues += dev.issues_closed_in_sprint
        totalStoryPoints += dev.story_points_closed_in_sprint
      })
    })

    return {
      sprintCount: sprints.length,
      developerCount: totalDevelopers.size,
      totalCommits,
      totalIssues,
      totalStoryPoints,
      avgCommitsPerSprint: Math.round(totalCommits / sprints.length),
      avgIssuesPerSprint: Math.round(totalIssues / sprints.length),
    }
  }, [sprintData])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-telus-purple"></div>
      </div>
    )
  }

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
        {/* Data Status Banner */}
        <div className={`rounded-xl shadow-lg p-6 mb-8 ${dataAvailable ? 'bg-green-50 border-2 border-green-200' : 'bg-yellow-50 border-2 border-yellow-200'}`}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">
                {dataAvailable ? '✓ Data Loaded Successfully' : '⚠ Data Not Available'}
              </h2>
              <p className="text-gray-600">
                {dataAvailable 
                  ? `Embedded data contains ${stats?.sprintCount} sprints with ${stats?.developerCount} developers`
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

        {stats && (
          <>
            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <MetricCard
                title="Total Sprints"
                value={stats.sprintCount}
                icon="📊"
                color="purple"
                subtitle="Tracked sprints"
              />
              <MetricCard
                title="Total Commits"
                value={stats.totalCommits.toLocaleString()}
                icon="💻"
                color="blue"
                subtitle={`Avg ${stats.avgCommitsPerSprint}/sprint`}
              />
              <MetricCard
                title="Issues Closed"
                value={stats.totalIssues}
                icon="✓"
                color="green"
                subtitle={`Avg ${stats.avgIssuesPerSprint}/sprint`}
              />
              <MetricCard
                title="Story Points"
                value={stats.totalStoryPoints}
                icon="🎯"
                color="orange"
                subtitle="Total delivered"
              />
            </div>

            {/* Summary Card */}
            <div className="mb-8">
              <SummaryCard
                title="Team Overview"
                icon="👥"
                items={[
                  { label: 'Active Developers', value: stats.developerCount, color: 'text-telus-purple' },
                  { label: 'Total Sprints', value: stats.sprintCount, color: 'text-telus-blue' },
                  { label: 'Commits', value: stats.totalCommits.toLocaleString(), color: 'text-telus-green' },
                  { label: 'Story Points', value: stats.totalStoryPoints, color: 'text-orange-600' },
                ]}
                footer={
                  <p className="text-sm text-gray-600 text-center">
                    Component demo - Full implementation in Phase 5+
                  </p>
                }
              />
            </div>

            {/* Chart Demos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <BarChart
                title="Sample Bar Chart"
                labels={['Commits', 'Issues', 'Story Points']}
                datasets={[
                  {
                    label: 'Team Metrics',
                    data: [stats.totalCommits / 10, stats.totalIssues, stats.totalStoryPoints],
                    backgroundColor: '#4B0082',
                  }
                ]}
              />
              <PieChart
                title="Sample Pie Chart"
                labels={['Commits', 'Issues Closed', 'Story Points']}
                data={[stats.totalCommits / 10, stats.totalIssues, stats.totalStoryPoints]}
              />
            </div>

            <RadarChart
              title="Sample Radar Chart"
              labels={['Commits', 'Issues', 'Story Points', 'Sprints', 'Developers']}
              datasets={[
                {
                  label: 'Team Metrics',
                  data: [
                    stats.totalCommits / 100,
                    stats.totalIssues,
                    stats.totalStoryPoints,
                    stats.sprintCount,
                    stats.developerCount
                  ],
                  backgroundColor: 'rgba(75, 0, 130, 0.2)',
                  borderColor: '#4B0082',
                }
              ]}
            />
          </>
        )}
      </div>
    </div>
  )
}
