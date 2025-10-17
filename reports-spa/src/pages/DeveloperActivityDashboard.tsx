import { useState, useEffect } from 'react'
import { getActivityData } from '@/data/embeddedData'
import type { DeveloperActivityData, DeveloperActivity } from '@/data/types'
import PieChart from '@/components/charts/PieChart'
import BarChart from '@/components/charts/BarChart'

interface ExtendedDeveloperActivity extends DeveloperActivity {
  avg_activity_per_sprint: number
}

export default function DeveloperActivityDashboard() {
  const [data, setData] = useState<DeveloperActivityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSprint, setSelectedSprint] = useState('all')

  useEffect(() => {
    const activityData = getActivityData()
    if (activityData) {
      setData(activityData)
    }
    setLoading(false)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-telus-purple"></div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-600 text-xl">Failed to load data</p>
      </div>
    )
  }

  const displayData: (DeveloperActivity | ExtendedDeveloperActivity)[] = selectedSprint === 'all' 
    ? data.developer_summary.map(dev => ({
        email: dev.email,
        name: dev.name,
        jira_actions: dev.total_jira_actions,
        repo_actions: dev.total_repo_actions,
        total_activity: dev.total_jira_actions + dev.total_repo_actions,
        avg_activity_per_sprint: dev.avg_activity_per_sprint,
        breakdown: {
          issues_created: 0,
          issues_updated: 0,
          status_changes: 0,
          commits: dev.total_commits
        }
      }))
    : data.sprint_activity[selectedSprint]?.developers || []

  const top10 = displayData.slice(0, 10)
  const pieData = {
    labels: top10.map(d => d.name.split(' ')[0]),
    data: top10.map(d => d.total_activity)
  }

  const barData = {
    labels: top10.map(d => d.name.split(' ')[0]),
    datasets: [
      {
        label: 'Jira Actions',
        data: top10.map(d => d.jira_actions),
        backgroundColor: '#4B0082'
      },
      {
        label: 'Repo Actions',
        data: top10.map(d => d.repo_actions),
        backgroundColor: '#66CC00'
      }
    ]
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="gradient-bg text-white py-12">
        <div className="container mx-auto px-6">
          <h1 className="text-4xl font-bold mb-4">Developer Activity Dashboard</h1>
          <p className="text-xl opacity-90">
            {data.metadata.total_developers} Developers • {data.metadata.total_sprints} Sprints
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Filter by Sprint</h3>
          <select
            value={selectedSprint}
            onChange={(e) => setSelectedSprint(e.target.value)}
            className="w-full md:w-auto px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-telus-purple"
          >
            <option value="all">All Sprints (Summary)</option>
            {Object.entries(data.sprint_activity).map(([sprintId, sprint]) => (
              <option key={sprintId} value={sprintId}>
                {sprint.sprint_name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-telus-purple">
            <p className="text-gray-600 text-sm font-medium">Last 3 Days Activity</p>
            <p className="text-3xl font-bold text-telus-purple mt-2">
              {data.last_3_days_activity.summary.total_activity}
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-telus-green">
            <p className="text-gray-600 text-sm font-medium">Active Developers</p>
            <p className="text-3xl font-bold text-telus-green mt-2">
              {data.last_3_days_activity.summary.active_developers}
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-telus-blue">
            <p className="text-gray-600 text-sm font-medium">Most Active (3 days)</p>
            <p className="text-lg font-bold text-telus-blue mt-2">
              {data.last_3_days_activity.summary.most_active_developer}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <PieChart
            labels={pieData.labels}
            data={pieData.data}
            title="📊 Activity Distribution (Top 10)"
          />
          <BarChart
            labels={barData.labels}
            datasets={barData.datasets}
            title="📈 Jira vs Repo Activity (Top 10)"
          />
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">
            {selectedSprint === 'all' ? 'All-Time Developer Summary' : 'Sprint Activity Details'}
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gradient-to-r from-telus-purple to-telus-light-purple text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Rank</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Developer</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">Total</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">Jira</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">Repo</th>
                  {selectedSprint === 'all' && (
                    <th className="px-4 py-3 text-center text-sm font-semibold">Avg/Sprint</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {displayData.map((dev, idx) => (
                  <tr key={dev.email} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                    <td className="px-4 py-3 text-center">
                      <div className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-telus-purple text-white font-bold text-sm">
                        {idx + 1}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{dev.name}</div>
                      <div className="text-gray-500 text-xs">{dev.email}</div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-telus-purple text-white">
                        {dev.total_activity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                        {dev.jira_actions}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                        {dev.repo_actions}
                      </span>
                    </td>
                    {selectedSprint === 'all' && 'avg_activity_per_sprint' in dev && (
                      <td className="px-4 py-3 text-center text-gray-700 font-medium">
                        {(dev as ExtendedDeveloperActivity).avg_activity_per_sprint.toFixed(1)}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8 text-center text-gray-600">
          <p className="text-sm">🎯 Developer Activity Dashboard</p>
          <p className="text-xs mt-2 opacity-75">Data reflects activity across Jira issues and Git commits</p>
        </div>
      </div>
    </div>
  )
}
