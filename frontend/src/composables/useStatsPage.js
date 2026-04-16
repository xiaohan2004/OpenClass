const moreStatCards = [
  {
    id: 'req',
    title: '请求统计',
    rows: [
      { label: '请求次数', value: '925.00' },
      { label: '消耗时间', value: '4.47 h' }
    ]
  },
  {
    id: 'all',
    title: '全局统计',
    rows: [
      { label: '消耗 Token', value: '42.63 M' },
      { label: '消耗费用', value: '10.06 $' }
    ]
  },
  {
    id: 'in',
    title: '输入统计',
    rows: [
      { label: '输入 Tokens', value: '42.30 M' },
      { label: '输入费用', value: '9.32 $' }
    ]
  },
  {
    id: 'out',
    title: '输出统计',
    rows: [
      { label: '输出 Tokens', value: '335.32 k' },
      { label: '输出费用', value: '0.74 $' }
    ]
  }
]

const trendMetrics = [
  { label: '请求次数', value: '925.00' },
  { label: '消耗金额', value: '10.06 $' },
  { label: 'Tokens 消耗', value: '42.63 M' }
]

const rankItems = [
  { medal: '1', name: 'longcat', value: '20.73 M' },
  { medal: '2', name: 'classroom-bot', value: '13.12 M' },
  { medal: '3', name: 'observer', value: '8.41 M' }
]

const heatmapDots = Array.from({ length: 132 }, (_, index) => {
  const hot = [113, 114, 115, 124, 125, 126, 127, 128, 129]
  const warm = [98, 99, 100, 101, 102, 103, 112, 116, 130]
  const cold = [95, 96, 97, 108, 109, 110, 111, 117, 118, 119]

  let level = 'is-idle'
  if (hot.includes(index)) {
    level = 'is-hot'
  } else if (warm.includes(index)) {
    level = 'is-warm'
  } else if (cold.includes(index)) {
    level = 'is-cold'
  }

  return {
    id: `dot-${index}`,
    level
  }
})

export function useStatsPage() {
  return {
    moreStatCards,
    trendMetrics,
    rankItems,
    heatmapDots
  }
}
