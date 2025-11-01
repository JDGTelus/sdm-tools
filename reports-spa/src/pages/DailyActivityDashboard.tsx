import { useState, useEffect } from 'react'
import { getDailyActivityData } from '@/data/embeddedData'
import { BarChart, MetricCard } from '@/components'

interface TimeBucket {
  jira: number
  repo: number
  total: number
}

interface Developer {
  name: string
  email: string
  buckets: {
    '10am-12pm': TimeBucket
    '12pm-2pm': TimeBucket
    '2pm-4pm': TimeBucket
    '4pm-6pm': TimeBucket
  }
  off_hours: TimeBucket
  daily_total: TimeBucket
}

interface DailyActivityReport {
  generated_at: string
  metadata: {
    report_date: string
    timezone: string
    time_buckets: string[]
    off_hours_window: string
  }
  developers: Developer[]
  summary: {
    total_developers: number
    total_activity: number
    total_jira_actions: number
    total_repo_actions: number
    most_active_bucket: string
    off_hours_activity: number
    off_hours_percentage: number
    bucket_totals: Record<string, number>
  }
}

export default function DailyActivityDashboard() {
  const [data, setData] = useState<DailyActivityReport | null>(null)
  const [loading, setLoading] = useState(true)

  // Map interval labels to display labels (cutoff times)
  const bucketDisplayNames: Record<string, string> = {
    '10am-12pm': '10am',
    '12pm-2pm': '12pm',
    '2pm-4pm': '2pm',
    '4pm-6pm': '4pm'
  }

  useEffect(() => {
    const dailyData = getDailyActivityData()
    if (dailyData) {
      setData(dailyData)
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
        <div className="text-center">
          <p className="text-red-600 text-xl mb-2">Daily activity data not available</p>
          <p className="text-gray-600">Generate the daily report using CLI option 5</p>
        </div>
      </div>
    )
  }

  const getIntensityColor = (total: number): string => {
    if (total === 0) return 'bg-gray-100 text-gray-400'
    if (total >= 10) return 'bg-green-600 text-white'
    if (total >= 5) return 'bg-green-400 text-gray-900'
    if (total >= 3) return 'bg-yellow-300 text-gray-900'
    return 'bg-blue-200 text-gray-900'
  }

  const getOffHoursColor = (total: number): string => {
    if (total === 0) return 'bg-gray-100 text-gray-400'
    if (total >= 5) return 'bg-orange-500 text-white'
    if (total >= 3) return 'bg-orange-300 text-gray-900'
    return 'bg-yellow-200 text-gray-900'
  }

  // Prepare chart data
  const bucketActivityData = {
    labels: [...data.metadata.time_buckets.map(b => bucketDisplayNames[b] || b), 'Off-Hours'],
    datasets: [
      {
        label: 'Jira Actions',
        data: [
          ...data.metadata.time_buckets.map(bucket => 
            data.developers.reduce((sum, dev) => sum + (dev.buckets[bucket as keyof typeof dev.buckets]?.jira || 0), 0)
          ),
          data.developers.reduce((sum, dev) => sum + dev.off_hours.jira, 0)
        ],
        backgroundColor: '#4B0082',
        borderColor: '#4B0082',
        borderWidth: 1,
      },
      {
        label: 'Repo Actions',
        data: [
          ...data.metadata.time_buckets.map(bucket => 
            data.developers.reduce((sum, dev) => sum + (dev.buckets[bucket as keyof typeof dev.buckets]?.repo || 0), 0)
          ),
          data.developers.reduce((sum, dev) => sum + dev.off_hours.repo, 0)
        ],
        backgroundColor: '#66CC00',
        borderColor: '#66CC00',
        borderWidth: 1,
      },
    ],
  }

  const activeDevelopers = data.developers.filter(d => d.daily_total.total > 0).slice(0, 15)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-telus-purple mb-2">Daily Activity Report</h1>
        <div className="text-gray-600 text-sm space-y-1">
          <p>Report Date: <span className="font-semibold">{data.metadata.report_date}</span></p>
          <p>Timezone: <span className="font-semibold">{data.metadata.timezone}</span></p>
          <p>Generated: <span className="font-semibold">{new Date(data.generated_at).toLocaleString()}</span></p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Developers"
          value={data.summary.total_developers}
          color="purple"
        />
        <MetricCard
          title="Total Activity"
          value={data.summary.total_activity}
          color="green"
        />
        <MetricCard
          title="Most Active Bucket"
          value={bucketDisplayNames[data.summary.most_active_bucket] || data.summary.most_active_bucket}
          color="blue"
        />
        <MetricCard
          title="Off-Hours Activity"
          value={`${data.summary.off_hours_percentage}%`}
          color="orange"
        />
      </div>

      {/* Activity Heatmap */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-telus-purple mb-4">Activity Heatmap</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200 text-sm">
            <thead className="bg-telus-purple text-white">
              <tr>
                <th className="px-4 py-3 text-left">Developer</th>
                {data.metadata.time_buckets.map(bucket => (
                  <th key={bucket} className="px-4 py-3 text-center">
                    {bucketDisplayNames[bucket] || bucket}
                  </th>
                ))}
                <th className="px-4 py-3 text-center bg-orange-600">Off-Hours</th>
                <th className="px-4 py-3 text-center bg-telus-green">Total</th>
              </tr>
            </thead>
            <tbody>
              {activeDevelopers.map((dev, idx) => (
                <tr key={idx} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{dev.name}</td>
                  {(['10am-12pm', '12pm-2pm', '2pm-4pm', '4pm-6pm'] as const).map(bucket => (
                    <td key={bucket} className={`px-4 py-2 text-center ${getIntensityColor(dev.buckets[bucket].total)}`}>
                      <div className="font-bold">{dev.buckets[bucket].total || '-'}</div>
                      {dev.buckets[bucket].total > 0 && (
                        <div className="text-xs">J:{dev.buckets[bucket].jira} R:{dev.buckets[bucket].repo}</div>
                      )}
                    </td>
                  ))}
                  <td className={`px-4 py-2 text-center ${getOffHoursColor(dev.off_hours.total)}`}>
                    <div className="font-bold">{dev.off_hours.total || '-'}</div>
                    {dev.off_hours.total > 0 && (
                      <div className="text-xs">J:{dev.off_hours.jira} R:{dev.off_hours.repo}</div>
                    )}
                  </td>
                  <td className="px-4 py-2 text-center bg-green-100 font-bold">
                    {dev.daily_total.total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-4 text-xs text-gray-600 flex gap-4">
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-green-600"></span> High (10+)
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-green-400"></span> Medium (5-9)
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-yellow-300"></span> Low (3-4)
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-blue-200"></span> Minimal (1-2)
            </span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <BarChart 
        labels={bucketActivityData.labels} 
        datasets={bucketActivityData.datasets}
        title="Activity by Time Bucket"
        stacked={true}
      />

      {/* Summary Statistics */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-telus-purple mb-4">Summary</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-telus-purple">{data.summary.total_jira_actions}</div>
            <div className="text-sm text-gray-600">Jira Actions</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-telus-green">{data.summary.total_repo_actions}</div>
            <div className="text-sm text-gray-600">Repo Actions</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-orange-500">{data.summary.off_hours_activity}</div>
            <div className="text-sm text-gray-600">Off-Hours Actions</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-telus-blue">
              {data.summary.bucket_totals[data.summary.most_active_bucket] || 0}
            </div>
            <div className="text-sm text-gray-600">Peak Bucket</div>
          </div>
        </div>
      </div>
    </div>
  )
}
