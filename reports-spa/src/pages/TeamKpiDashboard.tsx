import { useEffect, useState, useMemo } from 'react'
import { getSprintData } from '@/data/embeddedData'
import type { TeamSprintData, DeveloperMetrics } from '@/data/types'
import { MetricCard } from '@/components/shared'
import { BarChart } from '@/components/charts'

// KPI calculation logic
type KPIScore = 'excellent' | 'good' | 'fair' | 'needs-improvement' | 'no-delivery' | 'no-data'

interface DeveloperKPI {
  developer: DeveloperMetrics
  sprintName: string
  productivity: number
  productivityScore: KPIScore
  completionRate: number
  completionScore: KPIScore
  velocity: number
  velocityScore: KPIScore
  efficiency: number
  efficiencyScore: KPIScore
}

const calculateKPIs = (developer: DeveloperMetrics, sprintName: string): DeveloperKPI => {
  const commits = developer.commits_in_sprint || 0
  const assigned = developer.issues_assigned_in_sprint || 0
  const closed = developer.issues_closed_in_sprint || 0
  const storyPoints = developer.story_points_closed_in_sprint || 0

  return {
    developer,
    sprintName,
    // Productivity KPI: Commits per sprint (target: 10+)
    productivity: commits,
    productivityScore: commits >= 15 ? 'excellent' : commits >= 10 ? 'good' : commits >= 5 ? 'fair' : 'needs-improvement',
    
    // Completion Rate KPI: % of assigned issues closed
    completionRate: assigned > 0 ? Math.round((closed / assigned) * 100) : 0,
    completionScore: assigned > 0 
      ? (closed / assigned >= 0.8 ? 'excellent' 
        : closed / assigned >= 0.6 ? 'good' 
        : closed / assigned >= 0.4 ? 'fair' 
        : 'needs-improvement')
      : 'no-data',
    
    // Velocity KPI: Story points delivered
    velocity: storyPoints,
    velocityScore: storyPoints >= 10 ? 'excellent' : storyPoints >= 5 ? 'good' : storyPoints >= 2 ? 'fair' : storyPoints > 0 ? 'needs-improvement' : 'no-delivery',
    
    // Efficiency KPI: Story points per commit (quality indicator)
    efficiency: commits > 0 ? Math.round((storyPoints / commits) * 10) / 10 : 0,
    efficiencyScore: commits > 0 
      ? (storyPoints / commits >= 1 ? 'excellent' 
        : storyPoints / commits >= 0.5 ? 'good' 
        : storyPoints / commits >= 0.2 ? 'fair' 
        : 'needs-improvement')
      : 'no-data'
  }
}

const getScoreColor = (score: KPIScore): string => {
  switch(score) {
    case 'excellent': return 'text-green-600 bg-green-100'
    case 'good': return 'text-blue-600 bg-blue-100'
    case 'fair': return 'text-yellow-600 bg-yellow-100'
    case 'needs-improvement': return 'text-red-600 bg-red-100'
    case 'no-delivery': return 'text-gray-600 bg-gray-100'
    case 'no-data': return 'text-gray-400 bg-gray-50'
    default: return 'text-gray-600 bg-gray-100'
  }
}

const getScoreIcon = (score: KPIScore): string => {
  switch(score) {
    case 'excellent': return '🟢'
    case 'good': return '🔵'
    case 'fair': return '🟡'
    case 'needs-improvement': return '🔴'
    case 'no-delivery': return '⚪'
    case 'no-data': return '⚫'
    default: return '⚪'
  }
}

// KPI Card Component
interface KPICardProps {
  title: string
  value: number
  score: KPIScore
  unit?: string
  description: string
}

function KPICard({ title, value, score, unit = '', description }: KPICardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-gray-700">{title}</h4>
        <span className="text-lg">{getScoreIcon(score)}</span>
      </div>
      <div className="flex items-baseline space-x-2">
        <span className="text-2xl font-bold text-gray-900">{value}</span>
        {unit && <span className="text-sm text-gray-500">{unit}</span>}
      </div>
      <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-2 ${getScoreColor(score)}`}>
        {score.replace('-', ' ')}
      </div>
      <p className="text-xs text-gray-500 mt-2">{description}</p>
    </div>
  )
}

// Developer KPI Row Component
interface DeveloperKPIRowProps {
  kpis: DeveloperKPI
}

function DeveloperKPIRow({ kpis }: DeveloperKPIRowProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-4 card-hover">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{kpis.developer.name}</h3>
          <p className="text-sm text-gray-500">{kpis.developer.email}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-gray-700">Sprint: {kpis.sprintName}</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Productivity"
          value={kpis.productivity}
          score={kpis.productivityScore}
          unit="commits"
          description="Number of commits made during sprint. Target: 10+ commits"
        />
        <KPICard
          title="Completion Rate"
          value={kpis.completionRate}
          score={kpis.completionScore}
          unit="%"
          description="Percentage of assigned issues closed. Target: 80%+"
        />
        <KPICard
          title="Velocity"
          value={kpis.velocity}
          score={kpis.velocityScore}
          unit="points"
          description="Story points delivered. Target: 10+ points"
        />
        <KPICard
          title="Efficiency"
          value={kpis.efficiency}
          score={kpis.efficiencyScore}
          unit="pts/commit"
          description="Story points per commit. Target: 1.0+ pts/commit"
        />
      </div>
    </div>
  )
}

// Main Dashboard Component
export default function TeamKpiDashboard() {
  const [sprintData, setSprintData] = useState<TeamSprintData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSprint, setSelectedSprint] = useState<string>('')

  useEffect(() => {
    const data = getSprintData()
    setSprintData(data)
    setLoading(false)

    // Select the most recent sprint by default
    if (data) {
      const sprints = Object.entries(data.sprint_analytics)
        .sort(([, a], [, b]) => new Date(b.sprint_info.start_date).getTime() - new Date(a.sprint_info.start_date).getTime())
      if (sprints.length > 0) {
        setSelectedSprint(sprints[0][0])
      }
    }
  }, [])

  const availableSprints = useMemo(() => {
    if (!sprintData) return []
    return Object.entries(sprintData.sprint_analytics)
      .map(([key, sprint]) => ({
        key,
        name: sprint.sprint_info.name
      }))
      .sort((a, b) => b.key.localeCompare(a.key))
  }, [sprintData])

  const developerKPIs = useMemo(() => {
    if (!sprintData || !selectedSprint) return []
    
    const sprint = sprintData.sprint_analytics[selectedSprint]
    if (!sprint) return []

    return Object.values(sprint.developers)
      .map(dev => calculateKPIs(dev, sprint.sprint_info.name))
      .sort((a, b) => {
        // Sort by productivity first, then by velocity
        if (b.productivity !== a.productivity) return b.productivity - a.productivity
        return b.velocity - a.velocity
      })
  }, [sprintData, selectedSprint])

  const kpiSummary = useMemo(() => {
    if (developerKPIs.length === 0) return null

    const totalDevs = developerKPIs.length
    const excellentProductivity = developerKPIs.filter(k => k.productivityScore === 'excellent').length
    const excellentCompletion = developerKPIs.filter(k => k.completionScore === 'excellent').length
    const avgProductivity = Math.round(developerKPIs.reduce((sum, k) => sum + k.productivity, 0) / totalDevs)
    const avgCompletion = Math.round(developerKPIs.reduce((sum, k) => sum + k.completionRate, 0) / totalDevs)

    return {
      totalDevs,
      excellentProductivity,
      excellentCompletion,
      avgProductivity,
      avgCompletion
    }
  }, [developerKPIs])

  // Chart data for KPI distribution
  const kpiDistribution = useMemo(() => {
    if (developerKPIs.length === 0) return null

    const scores = ['excellent', 'good', 'fair', 'needs-improvement']
    const productivityCounts = scores.map(s => developerKPIs.filter(k => k.productivityScore === s).length)
    const completionCounts = scores.map(s => developerKPIs.filter(k => k.completionScore === s).length)

    return {
      labels: ['Excellent', 'Good', 'Fair', 'Needs Improvement'],
      datasets: [
        {
          label: 'Productivity',
          data: productivityCounts,
          backgroundColor: '#4B0082'
        },
        {
          label: 'Completion Rate',
          data: completionCounts,
          backgroundColor: '#66CC00'
        }
      ]
    }
  }, [developerKPIs])

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
          <p className="text-xl text-red-600 mb-4">No KPI data available</p>
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
          <h1 className="text-4xl font-bold mb-4">Team KPI Dashboard</h1>
          <p className="text-xl opacity-90">Key Performance Indicators & Metrics</p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Sprint Selector */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Sprint
          </label>
          <select
            value={selectedSprint}
            onChange={(e) => setSelectedSprint(e.target.value)}
            className="w-full md:w-96 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-telus-purple"
          >
            {availableSprints.map(sprint => (
              <option key={sprint.key} value={sprint.key}>
                {sprint.name}
              </option>
            ))}
          </select>
        </div>

        {/* KPI Summary */}
        {kpiSummary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <MetricCard
              title="Total Developers"
              value={kpiSummary.totalDevs}
              icon="👥"
              color="purple"
              subtitle="In selected sprint"
            />
            <MetricCard
              title="Excellent Productivity"
              value={kpiSummary.excellentProductivity}
              icon="🟢"
              color="green"
              subtitle={`${Math.round((kpiSummary.excellentProductivity / kpiSummary.totalDevs) * 100)}% of team`}
            />
            <MetricCard
              title="Excellent Completion"
              value={kpiSummary.excellentCompletion}
              icon="🟢"
              color="blue"
              subtitle={`${Math.round((kpiSummary.excellentCompletion / kpiSummary.totalDevs) * 100)}% of team`}
            />
            <MetricCard
              title="Avg Productivity"
              value={kpiSummary.avgProductivity}
              icon="💻"
              color="orange"
              subtitle={`${kpiSummary.avgCompletion}% avg completion`}
            />
          </div>
        )}

        {/* KPI Distribution Chart */}
        {kpiDistribution && (
          <div className="mb-8">
            <BarChart
              title="KPI Score Distribution"
              labels={kpiDistribution.labels}
              datasets={kpiDistribution.datasets}
            />
          </div>
        )}

        {/* Developer KPI Cards */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Developer KPIs</h2>
          <div className="space-y-4">
            {developerKPIs.map((kpis, idx) => (
              <DeveloperKPIRow key={idx} kpis={kpis} />
            ))}
          </div>
        </div>

        {/* KPI Legend */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">KPI Score Legend</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">🟢</span>
              <div>
                <p className="font-semibold text-green-600">Excellent</p>
                <p className="text-xs text-gray-600">Exceeds targets</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-2xl">🔵</span>
              <div>
                <p className="font-semibold text-blue-600">Good</p>
                <p className="text-xs text-gray-600">Meets targets</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-2xl">🟡</span>
              <div>
                <p className="font-semibold text-yellow-600">Fair</p>
                <p className="text-xs text-gray-600">Below targets</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-2xl">🔴</span>
              <div>
                <p className="font-semibold text-red-600">Needs Improvement</p>
                <p className="text-xs text-gray-600">Action required</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
