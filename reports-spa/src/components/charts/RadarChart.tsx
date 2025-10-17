import { useEffect, useRef } from 'react'
import type { Chart as ChartJS } from 'chart.js'
import {
  Chart,
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js'

// Register Chart.js components
Chart.register(
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
)

interface Dataset {
  label: string
  data: number[]
  backgroundColor?: string
  borderColor?: string
  pointBackgroundColor?: string
  pointBorderColor?: string
  pointHoverBackgroundColor?: string
  pointHoverBorderColor?: string
}

interface RadarChartProps {
  labels: string[]
  datasets: Dataset[]
  title?: string
  className?: string
}

export default function RadarChart({ labels, datasets, title, className = '' }: RadarChartProps) {
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
      type: 'radar',
      data: {
        labels,
        datasets: datasets.map(dataset => ({
          ...dataset,
          backgroundColor: dataset.backgroundColor || 'rgba(75, 0, 130, 0.2)',
          borderColor: dataset.borderColor || '#4B0082',
          pointBackgroundColor: dataset.pointBackgroundColor || '#4B0082',
          pointBorderColor: dataset.pointBorderColor || '#fff',
          pointHoverBackgroundColor: dataset.pointHoverBackgroundColor || '#fff',
          pointHoverBorderColor: dataset.pointHoverBorderColor || '#4B0082',
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            beginAtZero: true,
            ticks: {
              stepSize: 20,
              font: {
                size: 11
              }
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            },
            pointLabels: {
              font: {
                size: 12,
                weight: 500
              }
            }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              padding: 15,
              font: {
                size: 13,
                weight: 500
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
  }, [labels, datasets])

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
