import type { ReactNode } from 'react'

interface SummaryItem {
  label: string
  value: string | number
  color?: string
}

interface SummaryCardProps {
  title: string
  items: SummaryItem[]
  icon?: string | ReactNode
  footer?: ReactNode
  className?: string
}

export default function SummaryCard({
  title,
  items,
  icon,
  footer,
  className = ''
}: SummaryCardProps) {
  return (
    <div className={`card-hover bg-white rounded-xl shadow-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-gray-800">{title}</h3>
        {icon && (
          <div className="text-3xl text-telus-purple opacity-80">
            {typeof icon === 'string' ? icon : icon}
          </div>
        )}
      </div>

      {/* Items Grid */}
      <div className="grid grid-cols-2 gap-4">
        {items.map((item, index) => (
          <div key={index} className="text-center p-3 bg-gray-50 rounded-lg">
            <p className={`text-2xl font-bold ${item.color || 'text-telus-purple'}`}>
              {item.value}
            </p>
            <p className="text-sm text-gray-600 mt-1">{item.label}</p>
          </div>
        ))}
      </div>

      {/* Footer */}
      {footer && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          {footer}
        </div>
      )}
    </div>
  )
}
