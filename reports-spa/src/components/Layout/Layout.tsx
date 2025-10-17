import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import Sidebar from '@/components/Layout/Sidebar'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsCollapsed(true)
      } else {
        setIsCollapsed(false)
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
      
      <main
        className={`content-transition ${
          isCollapsed ? 'ml-16' : 'ml-64'
        } min-h-screen`}
      >
        {children}
      </main>
    </div>
  )
}
