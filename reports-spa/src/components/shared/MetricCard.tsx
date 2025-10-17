import type { ReactNode } from 'react'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: string | ReactNode
  trend?: {
    value: number
    label: string
  }
  color?: 'purple' | 'green' | 'blue' | 'orange' | 'red' | 'gray'
  className?: string
}

const colorClasses = {
  purple: {
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    text: 'text-telus-purple',
    icon: 'text-telus-purple',
  },
  green: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    text: 'text-telus-green',
    icon: 'text-telus-green',
  },
  blue: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-telus-blue',
    icon: 'text-telus-blue',
  },
  orange: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    text: 'text-orange-600',
    icon: 'text-orange-600',
  },
  red: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-600',
    icon: 'text-red-600',
  },
  gray: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-700',
    icon: 'text-gray-600',
  },
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  color = 'purple',
  className = ''
}: MetricCardProps) {
  const colors = colorClasses[color]

  return (
    <div className={`card-hover bg-white rounded-xl shadow-lg p-6 border-l-4 ${colors.border} ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <p className={`text-3xl font-bold ${colors.text} mb-2`}>{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className={`text-4xl ${colors.icon} opacity-80`}>
            {typeof icon === 'string' ? icon : icon}
          </div>
        )}
      </div>

      {trend && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center">
            <span className={`text-sm font-semibold ${trend.value >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}%
            </span>
            <span className="text-sm text-gray-500 ml-2">{trend.label}</span>
          </div>
        </div>
      )}
    </div>
  )
}
