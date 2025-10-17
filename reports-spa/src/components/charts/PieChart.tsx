import { useEffect, useRef } from 'react'
import type { Chart as ChartJS } from 'chart.js'
import {
  Chart,
  PieController,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js'

// Register Chart.js components
Chart.register(
  PieController,
  ArcElement,
  Tooltip,
  Legend
)

interface PieChartProps {
  labels: string[]
  data: number[]
  backgroundColor?: string[]
  title?: string
  className?: string
  showLegend?: boolean
}

const defaultColors = [
  '#4B0082', // telus-purple
  '#66CC00', // telus-green
  '#0066CC', // telus-blue
  '#8A2BE2', // telus-light-purple
  '#2E0054', // telus-dark-purple
  '#FF6B6B', // red
  '#4ECDC4', // teal
  '#FFD93D', // yellow
  '#95E1D3', // mint
  '#F38181', // pink
]

export default function PieChart({ 
  labels, 
  data, 
  backgroundColor,
  title, 
  className = '',
  showLegend = true
}: PieChartProps) {
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstance = useRef<ChartJS | null>(null)

  useEffect(() => {
    if (!chartRef.current) return

    // Destroy existing chart
    if (chartInstance.current) {
      chartInstance.current.destroy()
    }

    // Create new chart
    const ctx = chartRef.current.getContext('2d')
    if (!ctx) return

    chartInstance.current = new Chart(ctx, {
      type: 'pie',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: backgroundColor || defaultColors.slice(0, data.length),
          borderColor: '#fff',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: showLegend,
            position: 'right',
            labels: {
              padding: 15,
              font: {
                size: 12,
                weight: 500
              },
              generateLabels: (chart) => {
                const data = chart.data
                if (data.labels && data.datasets.length) {
                  return data.labels.map((label, i) => {
                    const value = data.datasets[0].data[i] as number
                    const total = (data.datasets[0].data as number[]).reduce((a, b) => a + b, 0)
                    const percentage = ((value / total) * 100).toFixed(1)
                    
                    return {
                      text: `${label}: ${percentage}%`,
                      fillStyle: (data.datasets[0].backgroundColor as string[])[i],
                      hidden: false,
                      index: i
                    }
                  })
                }
                return []
              }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleFont: {
              size: 14,
              weight: 'bold'
            },
            bodyFont: {
              size: 13
            },
            callbacks: {
              label: (context) => {
                const label = context.label || ''
                const value = context.parsed || 0
                const total = (context.dataset.data as number[]).reduce((a, b) => a + b, 0)
                const percentage = ((value / total) * 100).toFixed(1)
                return `${label}: ${value} (${percentage}%)`
              }
            }
          }
        }
      }
    })

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy()
      }
    }
  }, [labels, data, backgroundColor, showLegend])

  return (
    <div className={`bg-white rounded-xl shadow-lg p-6 ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>
      )}
      <div style={{ height: '350px' }}>
        <canvas ref={chartRef}></canvas>
      </div>
    </div>
  )
}
