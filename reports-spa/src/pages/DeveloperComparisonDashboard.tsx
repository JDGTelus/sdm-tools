import { useState, useEffect, useMemo } from 'react'
import { getSprintData, getActivityData } from '@/data/embeddedData'
import type { TeamSprintData, DeveloperActivityData, DeveloperMetrics } from '@/data/types'
import RadarChart from '@/components/charts/RadarChart'
import BarChart from '@/components/charts/BarChart'

interface DeveloperSummary {
  name: string
  email: string
  totalCommits: number
  totalIssuesAssigned: number
  totalIssuesClosed: number
  totalStoryPoints: number
  sprintCount: number
  avgCommits: number
  avgIssuesAssigned: number
  avgIssuesClosed: number
  avgStoryPoints: number
  completionRate: number
  activityPerSprint: number
}

interface PerformanceIndicator {
  color: string
  icon: string
  label: string
}

export default function DeveloperComparisonDashboard() {
  const [sprintData, setSprintData] = useState<TeamSprintData | null>(null)
  const [activityData, setActivityData] = useState<DeveloperActivityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedDeveloper, setSelectedDeveloper] = useState<DeveloperSummary | null>(null)
  const [selectedSprint, setSelectedSprint] = useState('all')

  useEffect(() => {
    const sprint = getSprintData()
    const activity = getActivityData()
    if (sprint && activity) {
      setSprintData(sprint)
      setActivityData(activity)
    }
    setLoading(false)
  }, [])

  const availableSprints = useMemo(() => {
    if (!sprintData?.sprint_analytics) return []
    
    return Object.entries(sprintData.sprint_analytics)
      .map(([key, sprint]) => ({
        key,
        name: sprint.sprint_info.name,
        state: sprint.sprint_info.state,
        startDate: sprint.sprint_info.start_date,
        endDate: sprint.sprint_info.end_date
      }))
      .sort((a, b) => new Date(b.startDate).getTime() - new Date(a.startDate).getTime())
  }, [sprintData])

  const teamMetrics = useMemo(() => {
    if (!sprintData?.sprint_analytics) return null

    let allDevs: DeveloperMetrics[] = []

    if (selectedSprint === 'all') {
      Object.values(sprintData.sprint_analytics).forEach(sprint => {
        Object.values(sprint.developers).forEach(dev => {
          allDevs.push(dev)
        })
      })
    } else {
      const sprint = sprintData.sprint_analytics[selectedSprint]
      if (sprint) {
        allDevs = Object.values(sprint.developers)
      }
    }

    const totalCommits = allDevs.reduce((sum, d) => sum + d.commits_in_sprint, 0)
    const totalIssuesAssigned = allDevs.reduce((sum, d) => sum + d.issues_assigned_in_sprint, 0)
    const totalIssuesClosed = allDevs.reduce((sum, d) => sum + d.issues_closed_in_sprint, 0)
    const totalStoryPoints = allDevs.reduce((sum, d) => sum + d.story_points_closed_in_sprint, 0)

    return {
      avgCommits: allDevs.length > 0 ? totalCommits / allDevs.length : 0,
      avgIssuesAssigned: allDevs.length > 0 ? totalIssuesAssigned / allDevs.length : 0,
      avgIssuesClosed: allDevs.length > 0 ? totalIssuesClosed / allDevs.length : 0,
      avgStoryPoints: allDevs.length > 0 ? totalStoryPoints / allDevs.length : 0,
      avgCompletionRate: totalIssuesAssigned > 0 ? (totalIssuesClosed / totalIssuesAssigned) * 100 : 0
    }
  }, [sprintData, selectedSprint])

  const developerSummaries = useMemo(() => {
    if (!sprintData?.sprint_analytics || !activityData?.developer_summary) return []

    const devMap: Record<string, DeveloperSummary> = {}

    if (selectedSprint === 'all') {
      Object.values(sprintData.sprint_analytics).forEach(sprint => {
        Object.values(sprint.developers).forEach(dev => {
          if (!devMap[dev.email]) {
            devMap[dev.email] = {
              name: dev.name,
              email: dev.email,
              totalCommits: 0,
              totalIssuesAssigned: 0,
              totalIssuesClosed: 0,
              totalStoryPoints: 0,
              sprintCount: 0,
              avgCommits: 0,
              avgIssuesAssigned: 0,
              avgIssuesClosed: 0,
              avgStoryPoints: 0,
              completionRate: 0,
              activityPerSprint: 0
            }
          }
          devMap[dev.email].totalCommits += dev.commits_in_sprint
          devMap[dev.email].totalIssuesAssigned += dev.issues_assigned_in_sprint
          devMap[dev.email].totalIssuesClosed += dev.issues_closed_in_sprint
          devMap[dev.email].totalStoryPoints += dev.story_points_closed_in_sprint
          devMap[dev.email].sprintCount += 1
        })
      })
    } else {
      const sprint = sprintData.sprint_analytics[selectedSprint]
      if (sprint) {
        Object.values(sprint.developers).forEach(dev => {
          devMap[dev.email] = {
            name: dev.name,
            email: dev.email,
            totalCommits: dev.commits_in_sprint,
            totalIssuesAssigned: dev.issues_assigned_in_sprint,
            totalIssuesClosed: dev.issues_closed_in_sprint,
            totalStoryPoints: dev.story_points_closed_in_sprint,
            sprintCount: 1,
            avgCommits: 0,
            avgIssuesAssigned: 0,
            avgIssuesClosed: 0,
            avgStoryPoints: 0,
            completionRate: 0,
            activityPerSprint: 0
          }
        })
      }
    }

    const summaries = Object.values(devMap).map(dev => {
      const activityInfo = activityData.developer_summary.find(d => d.email === dev.email)
      return {
        ...dev,
        avgCommits: dev.sprintCount > 0 ? dev.totalCommits / dev.sprintCount : 0,
        avgIssuesAssigned: dev.sprintCount > 0 ? dev.totalIssuesAssigned / dev.sprintCount : 0,
        avgIssuesClosed: dev.sprintCount > 0 ? dev.totalIssuesClosed / dev.sprintCount : 0,
        avgStoryPoints: dev.sprintCount > 0 ? dev.totalStoryPoints / dev.sprintCount : 0,
        completionRate: dev.totalIssuesAssigned > 0 ? (dev.totalIssuesClosed / dev.totalIssuesAssigned) * 100 : 0,
        activityPerSprint: activityInfo?.avg_activity_per_sprint || 0
      }
    })

    return summaries.sort((a, b) => (b.totalCommits + b.totalIssuesAssigned) - (a.totalCommits + a.totalIssuesAssigned))
  }, [sprintData, activityData, selectedSprint])

  const getPerformanceIndicator = (value: number, avg: number): PerformanceIndicator => {
    const ratio = avg > 0 ? (value / avg) * 100 : 100
    if (ratio >= 120) return { color: 'text-green-600', icon: '▲▲', label: 'Excellent' }
    if (ratio >= 100) return { color: 'text-green-500', icon: '▲', label: 'Above Avg' }
    if (ratio >= 80) return { color: 'text-yellow-600', icon: '●', label: 'Average' }
    return { color: 'text-red-500', icon: '▼', label: 'Below Avg' }
  }

  const radarData = useMemo(() => {
    if (!selectedDeveloper || !teamMetrics) return null

    const labelPrefix = selectedSprint === 'all' ? 'Avg ' : ''

    return {
      labels: [
        `${labelPrefix}Commits`,
        `${labelPrefix}Issues Assigned`,
        `${labelPrefix}Issues Closed`,
        `${labelPrefix}Story Points`,
        'Activity/Sprint'
      ],
      datasets: [
        {
          label: selectedDeveloper.name,
          data: [
            selectedDeveloper.avgCommits,
            selectedDeveloper.avgIssuesAssigned,
            selectedDeveloper.avgIssuesClosed,
            selectedDeveloper.avgStoryPoints,
            selectedDeveloper.activityPerSprint
          ],
          backgroundColor: 'rgba(75, 0, 130, 0.2)',
          borderColor: '#4B0082',
          pointBackgroundColor: '#4B0082'
        },
        {
          label: 'Team Average',
          data: [
            teamMetrics.avgCommits,
            teamMetrics.avgIssuesAssigned,
            teamMetrics.avgIssuesClosed,
            teamMetrics.avgStoryPoints,
            developerSummaries.reduce((sum, d) => sum + d.activityPerSprint, 0) / developerSummaries.length
          ],
          backgroundColor: 'rgba(102, 204, 0, 0.2)',
          borderColor: '#66CC00',
          pointBackgroundColor: '#66CC00'
        }
      ]
    }
  }, [selectedDeveloper, teamMetrics, developerSummaries, selectedSprint])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-telus-purple"></div>
      </div>
    )
  }

  if (!sprintData || !activityData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-600 text-xl">Failed to load data</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="gradient-bg text-white py-12">
        <div className="container mx-auto px-6">
          <h1 className="text-4xl font-bold mb-4">Developer Performance Comparison</h1>
          <p className="text-xl opacity-90">Individual Performance vs Team Benchmarks</p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Team Performance Benchmarks
            {selectedSprint !== 'all' && (
              <span className="text-base font-normal text-gray-600 ml-2">
                (for {availableSprints.find(s => s.key === selectedSprint)?.name})
              </span>
            )}
          </h2>
          <p className="text-sm text-gray-600 mb-6">
            {selectedSprint === 'all' 
              ? 'Averaged across all sprints and developers' 
              : 'Team average for selected sprint only'}
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-telus-purple">{teamMetrics?.avgCommits.toFixed(1)}</p>
              <p className="text-sm text-gray-600">Avg Commits/Sprint</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-telus-blue">{teamMetrics?.avgIssuesAssigned.toFixed(1)}</p>
              <p className="text-sm text-gray-600">Avg Issues Assigned</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-telus-green">{teamMetrics?.avgIssuesClosed.toFixed(1)}</p>
              <p className="text-sm text-gray-600">Avg Issues Closed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">{teamMetrics?.avgStoryPoints.toFixed(1)}</p>
              <p className="text-sm text-gray-600">Avg Story Points</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">{teamMetrics?.avgCompletionRate.toFixed(1)}%</p>
              <p className="text-sm text-gray-600">Avg Completion</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Filters</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sprint
              </label>
              <select
                value={selectedSprint}
                onChange={(e) => {
                  setSelectedSprint(e.target.value)
                  setSelectedDeveloper(null)
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-telus-purple"
              >
                <option value="all">All Sprints (Average)</option>
                {availableSprints.map(sprint => (
                  <option key={sprint.key} value={sprint.key}>
                    {sprint.name} ({sprint.state})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Developer
              </label>
              <select
                value={selectedDeveloper?.email || ''}
                onChange={(e) => setSelectedDeveloper(developerSummaries.find(d => d.email === e.target.value) || null)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-telus-purple"
              >
                <option value="">Choose a developer...</option>
                {developerSummaries.map(dev => (
                  <option key={dev.email} value={dev.email}>
                    {dev.name} {selectedSprint === 'all' ? `(${dev.sprintCount} sprints)` : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {selectedSprint !== 'all' && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                <span className="font-semibold">Sprint Context:</span>{' '}
                {availableSprints.find(s => s.key === selectedSprint)?.name} •{' '}
                {new Date(availableSprints.find(s => s.key === selectedSprint)?.startDate || '').toLocaleDateString()} -{' '}
                {new Date(availableSprints.find(s => s.key === selectedSprint)?.endDate || '').toLocaleDateString()}
              </p>
            </div>
          )}
        </div>

        {selectedDeveloper && teamMetrics && (
          <>
            <div className="bg-gradient-to-r from-telus-purple to-telus-light-purple rounded-xl shadow-lg p-8 mb-8 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-3xl font-bold mb-2">{selectedDeveloper.name}</h2>
                  <p className="text-lg opacity-90">{selectedDeveloper.email}</p>
                  <p className="text-sm opacity-75 mt-2">
                    {selectedSprint === 'all' 
                      ? `Average across ${selectedDeveloper.sprintCount} sprint${selectedDeveloper.sprintCount !== 1 ? 's' : ''}`
                      : `Performance in ${availableSprints.find(s => s.key === selectedSprint)?.name}`
                    }
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-5xl font-bold">{selectedDeveloper.completionRate.toFixed(0)}%</p>
                  <p className="text-sm opacity-90">Completion Rate</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-gray-600 text-sm font-medium">
                    {selectedSprint === 'all' ? 'Avg Commits/Sprint' : 'Commits'}
                  </p>
                  <span className={`${getPerformanceIndicator(selectedDeveloper.avgCommits, teamMetrics.avgCommits).color} text-xl font-bold`}>
                    {getPerformanceIndicator(selectedDeveloper.avgCommits, teamMetrics.avgCommits).icon}
                  </span>
                </div>
                <p className="text-3xl font-bold text-telus-purple">{selectedDeveloper.avgCommits.toFixed(1)}</p>
                <p className="text-sm text-gray-500 mt-1">
                  Team {selectedSprint === 'all' ? 'avg' : 'avg in sprint'}: {teamMetrics.avgCommits.toFixed(1)}
                </p>
                <div className="mt-3 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-telus-purple rounded-full h-2" 
                    style={{width: `${Math.min(100, (selectedDeveloper.avgCommits / teamMetrics.avgCommits) * 100)}%`}}
                  ></div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-gray-600 text-sm font-medium">
                    {selectedSprint === 'all' ? 'Avg Issues Assigned' : 'Issues Assigned'}
                  </p>
                  <span className={`${getPerformanceIndicator(selectedDeveloper.avgIssuesAssigned, teamMetrics.avgIssuesAssigned).color} text-xl font-bold`}>
                    {getPerformanceIndicator(selectedDeveloper.avgIssuesAssigned, teamMetrics.avgIssuesAssigned).icon}
                  </span>
                </div>
                <p className="text-3xl font-bold text-telus-blue">{selectedDeveloper.avgIssuesAssigned.toFixed(1)}</p>
                <p className="text-sm text-gray-500 mt-1">
                  Team {selectedSprint === 'all' ? 'avg' : 'avg in sprint'}: {teamMetrics.avgIssuesAssigned.toFixed(1)}
                </p>
                <div className="mt-3 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-telus-blue rounded-full h-2" 
                    style={{width: `${Math.min(100, (selectedDeveloper.avgIssuesAssigned / teamMetrics.avgIssuesAssigned) * 100)}%`}}
                  ></div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-gray-600 text-sm font-medium">
                    {selectedSprint === 'all' ? 'Avg Issues Closed' : 'Issues Closed'}
                  </p>
                  <span className={`${getPerformanceIndicator(selectedDeveloper.avgIssuesClosed, teamMetrics.avgIssuesClosed).color} text-xl font-bold`}>
                    {getPerformanceIndicator(selectedDeveloper.avgIssuesClosed, teamMetrics.avgIssuesClosed).icon}
                  </span>
                </div>
                <p className="text-3xl font-bold text-telus-green">{selectedDeveloper.avgIssuesClosed.toFixed(1)}</p>
                <p className="text-sm text-gray-500 mt-1">
                  Team {selectedSprint === 'all' ? 'avg' : 'avg in sprint'}: {teamMetrics.avgIssuesClosed.toFixed(1)}
                </p>
                <div className="mt-3 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-telus-green rounded-full h-2" 
                    style={{width: `${Math.min(100, (selectedDeveloper.avgIssuesClosed / teamMetrics.avgIssuesClosed) * 100)}%`}}
                  ></div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-gray-600 text-sm font-medium">
                    {selectedSprint === 'all' ? 'Avg Story Points' : 'Story Points'}
                  </p>
                  <span className={`${getPerformanceIndicator(selectedDeveloper.avgStoryPoints, teamMetrics.avgStoryPoints).color} text-xl font-bold`}>
                    {getPerformanceIndicator(selectedDeveloper.avgStoryPoints, teamMetrics.avgStoryPoints).icon}
                  </span>
                </div>
                <p className="text-3xl font-bold text-orange-600">{selectedDeveloper.avgStoryPoints.toFixed(1)}</p>
                <p className="text-sm text-gray-500 mt-1">
                  Team {selectedSprint === 'all' ? 'avg' : 'avg in sprint'}: {teamMetrics.avgStoryPoints.toFixed(1)}
                </p>
                <div className="mt-3 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-orange-600 rounded-full h-2" 
                    style={{width: `${Math.min(100, (selectedDeveloper.avgStoryPoints / teamMetrics.avgStoryPoints) * 100)}%`}}
                  ></div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {radarData && (
                <RadarChart 
                  labels={radarData.labels}
                  datasets={radarData.datasets}
                  title="Performance Profile Comparison"
                />
              )}
              <BarChart
                labels={['Commits', 'Issues Assigned', 'Issues Closed', 'Story Points']}
                datasets={[
                  {
                    label: selectedDeveloper.name,
                    data: [
                      selectedDeveloper.totalCommits,
                      selectedDeveloper.totalIssuesAssigned,
                      selectedDeveloper.totalIssuesClosed,
                      selectedDeveloper.totalStoryPoints
                    ],
                    backgroundColor: '#4B0082'
                  },
                  {
                    label: selectedSprint === 'all' ? 'Team Average (per dev)' : 'Team Average',
                    data: [
                      teamMetrics.avgCommits * selectedDeveloper.sprintCount,
                      teamMetrics.avgIssuesAssigned * selectedDeveloper.sprintCount,
                      teamMetrics.avgIssuesClosed * selectedDeveloper.sprintCount,
                      teamMetrics.avgStoryPoints * selectedDeveloper.sprintCount
                    ],
                    backgroundColor: '#66CC00'
                  }
                ]}
                title={selectedSprint === 'all' ? 'Total Contributions vs Team Benchmark' : 'Sprint Performance vs Team Average'}
              />
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">
                Performance Summary
                {selectedSprint !== 'all' && (
                  <span className="text-sm font-normal text-gray-600 ml-2">
                    (Sprint-specific)
                  </span>
                )}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <h4 className="font-semibold text-gray-700 mb-3">Strengths</h4>
                  <ul className="space-y-2">
                    {selectedDeveloper.avgCommits >= teamMetrics.avgCommits && (
                      <li className="flex items-center text-green-600">
                        <span className="mr-2">✓</span>
                        <span className="text-sm">
                          {selectedSprint === 'all' 
                            ? 'Above average commit activity' 
                            : 'Above team average in commits'}
                        </span>
                      </li>
                    )}
                    {selectedDeveloper.avgIssuesClosed >= teamMetrics.avgIssuesClosed && (
                      <li className="flex items-center text-green-600">
                        <span className="mr-2">✓</span>
                        <span className="text-sm">Strong issue completion rate</span>
                      </li>
                    )}
                    {selectedDeveloper.avgStoryPoints >= teamMetrics.avgStoryPoints && (
                      <li className="flex items-center text-green-600">
                        <span className="mr-2">✓</span>
                        <span className="text-sm">Above average story points delivery</span>
                      </li>
                    )}
                    {selectedDeveloper.completionRate >= teamMetrics.avgCompletionRate && (
                      <li className="flex items-center text-green-600">
                        <span className="mr-2">✓</span>
                        <span className="text-sm">High task completion rate</span>
                      </li>
                    )}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-700 mb-3">Key Metrics</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>
                      {selectedSprint === 'all' ? 'Total' : 'Sprint'} Commits: 
                      <span className="font-semibold text-gray-800"> {selectedDeveloper.totalCommits}</span>
                    </li>
                    <li>
                      {selectedSprint === 'all' ? 'Total' : 'Sprint'} Issues Closed: 
                      <span className="font-semibold text-gray-800"> {selectedDeveloper.totalIssuesClosed}</span>
                    </li>
                    <li>
                      {selectedSprint === 'all' ? 'Total' : 'Sprint'} Story Points: 
                      <span className="font-semibold text-gray-800"> {selectedDeveloper.totalStoryPoints.toFixed(1)}</span>
                    </li>
                    {selectedSprint === 'all' && (
                      <li>
                        Sprint Participation: 
                        <span className="font-semibold text-gray-800"> {selectedDeveloper.sprintCount} sprints</span>
                      </li>
                    )}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-700 mb-3">Improvement Areas</h4>
                  <ul className="space-y-2">
                    {selectedDeveloper.avgCommits < teamMetrics.avgCommits && (
                      <li className="flex items-center text-orange-600">
                        <span className="mr-2">→</span>
                        <span className="text-sm">Consider increasing commit frequency</span>
                      </li>
                    )}
                    {selectedDeveloper.avgIssuesClosed < teamMetrics.avgIssuesClosed && (
                      <li className="flex items-center text-orange-600">
                        <span className="mr-2">→</span>
                        <span className="text-sm">Focus on completing assigned issues</span>
                      </li>
                    )}
                    {selectedDeveloper.avgStoryPoints < teamMetrics.avgStoryPoints && (
                      <li className="flex items-center text-orange-600">
                        <span className="mr-2">→</span>
                        <span className="text-sm">Work on higher value tasks</span>
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          </>
        )}

        <div className="bg-white rounded-xl shadow-lg p-6 mt-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Team Performance Overview</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gradient-to-r from-telus-purple to-telus-light-purple text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Developer</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">
                    {selectedSprint === 'all' ? 'Sprints' : 'Participated'}
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">
                    {selectedSprint === 'all' ? 'Avg Commits' : 'Commits'}
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">
                    {selectedSprint === 'all' ? 'Avg Issues' : 'Issues'}
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">
                    {selectedSprint === 'all' ? 'Avg Closed' : 'Closed'}
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">
                    {selectedSprint === 'all' ? 'Avg Points' : 'Points'}
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">Completion %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {developerSummaries.map((dev, idx) => (
                  <tr 
                    key={dev.email} 
                    className={`${idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'} hover:bg-blue-50 cursor-pointer transition-colors`}
                    onClick={() => setSelectedDeveloper(dev)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{dev.name}</div>
                      <div className="text-gray-500 text-xs">{dev.email}</div>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-700">{dev.sprintCount}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-semibold ${getPerformanceIndicator(dev.avgCommits, teamMetrics?.avgCommits || 0).color}`}>
                        {dev.avgCommits.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-semibold ${getPerformanceIndicator(dev.avgIssuesAssigned, teamMetrics?.avgIssuesAssigned || 0).color}`}>
                        {dev.avgIssuesAssigned.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-semibold ${getPerformanceIndicator(dev.avgIssuesClosed, teamMetrics?.avgIssuesClosed || 0).color}`}>
                        {dev.avgIssuesClosed.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-semibold ${getPerformanceIndicator(dev.avgStoryPoints, teamMetrics?.avgStoryPoints || 0).color}`}>
                        {dev.avgStoryPoints.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                        dev.completionRate >= 80 ? 'bg-green-100 text-green-800' :
                        dev.completionRate >= 50 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {dev.completionRate.toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8 text-center text-gray-600">
          <p className="text-sm">Developer Performance Comparison Dashboard</p>
          <p className="text-xs mt-2 opacity-75">Click on any developer in the table to view detailed comparison</p>
        </div>
      </div>
    </div>
  )
}
