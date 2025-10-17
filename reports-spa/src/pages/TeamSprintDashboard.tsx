import { useEffect, useState, useMemo } from 'react'
import { getSprintData } from '@/data/embeddedData'
import type { TeamSprintData, SprintAnalytics } from '@/data/types'
import { MetricCard, SummaryCard } from '@/components/shared'
import { BarChart } from '@/components/charts'

// Utility functions
const formatDate = (dateString: string): string => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return 'N/A'
  }
}

const getSprintStatusColor = (state: string): string => {
  switch (state?.toLowerCase()) {
    case 'active': return 'bg-green-100 text-green-800'
    case 'closed': return 'bg-gray-100 text-gray-800'
    case 'future': return 'bg-blue-100 text-blue-800'
    default: return 'bg-gray-100 text-gray-600'
  }
}

// Sprint Filter Component
interface SprintFilterProps {
  sprints: Array<{ key: string; info: SprintAnalytics['sprint_info'] }>
  selectedSprints: string[]
  onSprintToggle: (key: string) => void
  onSelectAll: () => void
  onClearAll: () => void
}

function SprintFilter({ sprints, selectedSprints, onSprintToggle, onSelectAll, onClearAll }: SprintFilterProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center">
          <span className="text-telus-purple mr-2">🎯</span>
          Sprint Filter ({selectedSprints.length} of {sprints.length} selected)
        </h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-telus-purple hover:text-telus-light-purple transition-colors"
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={onSelectAll}
          className="px-3 py-1 bg-telus-purple text-white rounded-lg text-sm hover:bg-telus-light-purple transition-colors"
        >
          Select All
        </button>
        <button
          onClick={onClearAll}
          className="px-3 py-1 bg-gray-500 text-white rounded-lg text-sm hover:bg-gray-600 transition-colors"
        >
          Clear All
        </button>
      </div>

      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-60 overflow-y-auto">
          {sprints.map((sprint) => (
            <label key={sprint.key} className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedSprints.includes(sprint.key)}
                onChange={() => onSprintToggle(sprint.key)}
                className="w-4 h-4 text-telus-purple border-gray-300 rounded focus:ring-telus-purple"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {sprint.info.name}
                  </span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getSprintStatusColor(sprint.info.state)}`}>
                    {sprint.info.state}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  {formatDate(sprint.info.start_date)} - {formatDate(sprint.info.end_date)}
                </div>
              </div>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

// Sprint Overview Card Component
interface SprintOverviewCardProps {
  sprint: SprintAnalytics
}

function SprintOverviewCard({ sprint }: SprintOverviewCardProps) {
  const totalDevelopers = Object.keys(sprint.developers).length
  const totalCommits = Object.values(sprint.developers).reduce((sum, dev) => sum + dev.commits_in_sprint, 0)
  const totalIssuesAssigned = Object.values(sprint.developers).reduce((sum, dev) => sum + dev.issues_assigned_in_sprint, 0)
  const totalIssuesClosed = Object.values(sprint.developers).reduce((sum, dev) => sum + dev.issues_closed_in_sprint, 0)
  const totalStoryPoints = Object.values(sprint.developers).reduce((sum, dev) => sum + dev.story_points_closed_in_sprint, 0)
  const completionRate = totalIssuesAssigned > 0 ? ((totalIssuesClosed / totalIssuesAssigned) * 100).toFixed(1) : '0'

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 card-hover mb-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-800">{sprint.sprint_info.name}</h3>
          <p className="text-gray-600 text-sm">
            {formatDate(sprint.sprint_info.start_date)} - {formatDate(sprint.sprint_info.end_date)}
          </p>
        </div>
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getSprintStatusColor(sprint.sprint_info.state)}`}>
          {sprint.sprint_info.state}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="text-center">
          <p className="text-2xl font-bold text-telus-purple">{totalDevelopers}</p>
          <p className="text-xs text-gray-600">Developers</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-telus-green">{totalCommits}</p>
          <p className="text-xs text-gray-600">Commits</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-telus-blue">{totalIssuesAssigned}</p>
          <p className="text-xs text-gray-600">Issues Assigned</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-orange-600">{totalIssuesClosed}</p>
          <p className="text-xs text-gray-600">Issues Closed</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-purple-600">{totalStoryPoints}</p>
          <p className="text-xs text-gray-600">Story Points</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-indigo-600">{completionRate}%</p>
          <p className="text-xs text-gray-600">Completion</p>
        </div>
      </div>
    </div>
  )
}

// Main Dashboard Component
export default function TeamSprintDashboard() {
  const [sprintData, setSprintData] = useState<TeamSprintData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSprints, setSelectedSprints] = useState<string[]>([])

  useEffect(() => {
    const data = getSprintData()
    setSprintData(data)
    setLoading(false)

    // Select all sprints by default
    if (data) {
      setSelectedSprints(Object.keys(data.sprint_analytics))
    }
  }, [])

  const availableSprints = useMemo(() => {
    if (!sprintData) return []
    return Object.entries(sprintData.sprint_analytics).map(([key, sprint]) => ({
      key,
      info: sprint.sprint_info
    })).sort((a, b) => new Date(b.info.start_date).getTime() - new Date(a.info.start_date).getTime())
  }, [sprintData])

  const filteredSprints = useMemo(() => {
    if (!sprintData) return []
    return selectedSprints.map(key => sprintData.sprint_analytics[key]).filter(Boolean)
  }, [sprintData, selectedSprints])

  const aggregatedStats = useMemo(() => {
    const allDevelopers = new Set<string>()
    let totalCommits = 0
    let totalIssuesAssigned = 0
    let totalIssuesClosed = 0
    let totalStoryPoints = 0

    filteredSprints.forEach(sprint => {
      Object.values(sprint.developers).forEach(dev => {
        allDevelopers.add(dev.email)
        totalCommits += dev.commits_in_sprint
        totalIssuesAssigned += dev.issues_assigned_in_sprint
        totalIssuesClosed += dev.issues_closed_in_sprint
        totalStoryPoints += dev.story_points_closed_in_sprint
      })
    })

    const completionRate = totalIssuesAssigned > 0 ? ((totalIssuesClosed / totalIssuesAssigned) * 100).toFixed(1) : '0'

    return {
      developerCount: allDevelopers.size,
      totalCommits,
      totalIssuesAssigned,
      totalIssuesClosed,
      totalStoryPoints,
      completionRate,
      avgCommitsPerSprint: filteredSprints.length > 0 ? Math.round(totalCommits / filteredSprints.length) : 0,
      avgIssuesPerSprint: filteredSprints.length > 0 ? Math.round(totalIssuesAssigned / filteredSprints.length) : 0
    }
  }, [filteredSprints])

  // Chart data for top performers
  const topPerformersData = useMemo(() => {
    const developerStats = new Map<string, { commits: number; issues: number; points: number }>()

    filteredSprints.forEach(sprint => {
      Object.values(sprint.developers).forEach(dev => {
        const existing = developerStats.get(dev.name) || { commits: 0, issues: 0, points: 0 }
        developerStats.set(dev.name, {
          commits: existing.commits + dev.commits_in_sprint,
          issues: existing.issues + dev.issues_closed_in_sprint,
          points: existing.points + dev.story_points_closed_in_sprint
        })
      })
    })

    const sorted = Array.from(developerStats.entries())
      .sort((a, b) => b[1].commits - a[1].commits)
      .slice(0, 10)

    return {
      labels: sorted.map(([name]) => name.split(' ')[0]),
      datasets: [
        {
          label: 'Commits',
          data: sorted.map(([, stats]) => stats.commits),
          backgroundColor: '#4B0082'
        }
      ]
    }
  }, [filteredSprints])

  const handleSprintToggle = (key: string) => {
    setSelectedSprints(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    )
  }

  const handleSelectAll = () => {
    setSelectedSprints(availableSprints.map(s => s.key))
  }

  const handleClearAll = () => {
    setSelectedSprints([])
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-telus-purple"></div>
      </div>
    )
  }

  if (!sprintData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-red-600 mb-4">No sprint data available</p>
          <p className="text-gray-600">Please build with data files present</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="gradient-bg text-white py-12">
        <div className="container mx-auto px-6">
          <h1 className="text-4xl font-bold mb-4">Team Sprint Dashboard</h1>
          <p className="text-xl opacity-90">Sprint Analytics & Performance Insights</p>
          <p className="text-sm opacity-75 mt-2">
            Analyzing {selectedSprints.length} sprint{selectedSprints.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Sprint Filter */}
        <SprintFilter
          sprints={availableSprints}
          selectedSprints={selectedSprints}
          onSprintToggle={handleSprintToggle}
          onSelectAll={handleSelectAll}
          onClearAll={handleClearAll}
        />

        {selectedSprints.length === 0 ? (
          <div className="bg-yellow-50 border-2 border-yellow-200 rounded-xl p-8 text-center">
            <p className="text-xl font-semibold text-yellow-800 mb-2">No Sprints Selected</p>
            <p className="text-yellow-700">Please select at least one sprint to view analytics</p>
          </div>
        ) : (
          <>
            {/* Aggregated Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <MetricCard
                title="Total Commits"
                value={aggregatedStats.totalCommits.toLocaleString()}
                icon="💻"
                color="green"
                subtitle={`Avg ${aggregatedStats.avgCommitsPerSprint}/sprint`}
              />
              <MetricCard
                title="Issues Closed"
                value={aggregatedStats.totalIssuesClosed}
                icon="✓"
                color="blue"
                subtitle={`${aggregatedStats.completionRate}% completion`}
              />
              <MetricCard
                title="Story Points"
                value={aggregatedStats.totalStoryPoints}
                icon="🎯"
                color="orange"
                subtitle="Total delivered"
              />
              <MetricCard
                title="Active Developers"
                value={aggregatedStats.developerCount}
                icon="👥"
                color="purple"
                subtitle="Team members"
              />
            </div>

            {/* Summary Card */}
            <div className="mb-8">
              <SummaryCard
                title="Sprint Overview"
                icon="📊"
                items={[
                  { label: 'Sprints Analyzed', value: selectedSprints.length, color: 'text-telus-purple' },
                  { label: 'Total Commits', value: aggregatedStats.totalCommits.toLocaleString(), color: 'text-telus-green' },
                  { label: 'Issues Closed', value: aggregatedStats.totalIssuesClosed, color: 'text-telus-blue' },
                  { label: 'Story Points', value: aggregatedStats.totalStoryPoints, color: 'text-orange-600' }
                ]}
              />
            </div>

            {/* Top Performers Chart */}
            {topPerformersData.labels.length > 0 && (
              <div className="mb-8">
                <BarChart
                  title="Top 10 Contributors by Commits"
                  labels={topPerformersData.labels}
                  datasets={topPerformersData.datasets}
                />
              </div>
            )}

            {/* Individual Sprint Cards */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Sprint Details</h2>
              <div className="space-y-4">
                {filteredSprints.map((sprint, idx) => (
                  <SprintOverviewCard key={idx} sprint={sprint} />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
