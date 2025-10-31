import { Link, useLocation } from 'react-router-dom'

interface MenuItem {
  path: string
  label: string
  icon: string
}

const menuItems: MenuItem[] = [
  { path: '/', label: 'Team Sprint Dashboard', icon: '📊' },
  { path: '/kpi', label: 'Team KPI Dashboard', icon: '📈' },
  { path: '/activity', label: 'Developer Activity', icon: '👥' },
  { path: '/comparison', label: 'Developer Comparison', icon: '⚖️' },
  { path: '/daily', label: 'Daily Activity Report', icon: '📅' }
]

interface SidebarProps {
  isCollapsed: boolean
  setIsCollapsed: (value: boolean) => void
}

export default function Sidebar({ isCollapsed, setIsCollapsed }: SidebarProps) {
  const location = useLocation()

  const isActive = (path: string) => {
    return location.pathname === path
  }

  return (
    <div
      className={`sidebar-transition bg-gradient-to-b from-telus-purple to-telus-dark-purple text-white h-screen fixed left-0 top-0 ${
        isCollapsed ? 'w-16' : 'w-64'
      } flex flex-col shadow-2xl z-50`}
    >
      {/* Header */}
      <div className="p-4 border-b border-telus-light-purple">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <h1 className="text-xl font-bold">SDM Reports</h1>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-2 rounded-lg hover:bg-telus-light-purple transition-colors"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? '→' : '←'}
          </button>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-2 px-2">
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`flex items-center px-3 py-3 rounded-lg transition-all ${
                  isActive(item.path)
                    ? 'bg-telus-green text-white shadow-lg'
                    : 'hover:bg-telus-light-purple hover:shadow-md'
                }`}
              >
                <span className="text-2xl">{item.icon}</span>
                {!isCollapsed && (
                  <span className="ml-3 font-medium">{item.label}</span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-telus-light-purple">
        {!isCollapsed ? (
          <div className="text-xs text-gray-300">
            <p className="font-semibold">SDM-Tools</p>
            <p className="opacity-75">Reports SPA v1.0</p>
          </div>
        ) : (
          <div className="text-center text-xs text-gray-300">
            v1
          </div>
        )}
      </div>
    </div>
  )
}
