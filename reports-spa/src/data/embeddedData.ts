import type { TeamSprintData, DeveloperActivityData } from './types'

/**
 * Access embedded sprint data from window globals
 * Data is injected at build time via Vite plugin
 */
export function getSprintData(): TeamSprintData | null {
  if (typeof window !== 'undefined' && window.__SPRINT_DATA__) {
    return window.__SPRINT_DATA__
  }
  
  console.warn('Sprint data not found. Data should be embedded at build time.')
  return null
}

/**
 * Access embedded developer activity data from window globals
 * Data is injected at build time via Vite plugin
 */
export function getActivityData(): DeveloperActivityData | null {
  if (typeof window !== 'undefined' && window.__ACTIVITY_DATA__) {
    return window.__ACTIVITY_DATA__
  }
  
  console.warn('Activity data not found. Data should be embedded at build time.')
  return null
}

/**
 * Get all embedded data at once
 */
export function getAllData() {
  return {
    sprintData: getSprintData(),
    activityData: getActivityData(),
  }
}

/**
 * Check if data is available
 */
export function isDataAvailable(): boolean {
  return !!(window.__SPRINT_DATA__ && window.__ACTIVITY_DATA__)
}
