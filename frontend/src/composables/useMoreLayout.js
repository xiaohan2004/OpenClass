const moreNavItems = [
  { id: 'stats', symbol: '📊', label: '统计' },
  { id: 'logs', symbol: '🧾', label: '日志' },
  { id: 'settings', symbol: '⚙️', label: '设置' }
]

const moreViewTitleMap = {
  stats: '统计',
  logs: '日志',
  settings: '设置'
}

export function useMoreLayout() {
  return {
    moreNavItems,
    moreViewTitleMap
  }
}
