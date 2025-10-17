import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// Plugin to embed JSON data at build time
function embedDataPlugin() {
  return {
    name: 'embed-data',
    transformIndexHtml(html: string) {
      // Paths to JSON data files
      const sprintDataPath = path.resolve(__dirname, '../ux/web/data/team_sprint_stats.json')
      const activityDataPath = path.resolve(__dirname, '../ux/web/data/developer_activity.json')
      
      let sprintData = '{}'
      let activityData = '{}'
      
      // Read JSON files if they exist
      try {
        if (fs.existsSync(sprintDataPath)) {
          sprintData = fs.readFileSync(sprintDataPath, 'utf-8')
        } else {
          console.warn('⚠️  Sprint data not found:', sprintDataPath)
        }
        
        if (fs.existsSync(activityDataPath)) {
          activityData = fs.readFileSync(activityDataPath, 'utf-8')
        } else {
          console.warn('⚠️  Activity data not found:', activityDataPath)
        }
      } catch (error) {
        console.error('Error reading data files:', error)
      }
      
      // Inject data as global variables in <head>
      const dataScript = `
    <script>
      window.__SPRINT_DATA__ = ${sprintData};
      window.__ACTIVITY_DATA__ = ${activityData};
    </script>`
      
      return html.replace('</head>', `${dataScript}\n  </head>`)
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), embedDataPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../dist/reports',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Create single bundle for self-contained deployment
        manualChunks: undefined,
      }
    }
  }
})
