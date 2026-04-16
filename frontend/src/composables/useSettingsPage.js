const settingSections = [
  {
    id: 'classroom',
    title: '课堂参数',
    fields: [
      { key: 'askInterval', label: '提问间隔', value: '20 秒' },
      { key: 'summaryWindow', label: '摘要窗口', value: '120 秒' },
      { key: 'maxQueue', label: '队列上限', value: '12 条' }
    ]
  },
  {
    id: 'audio',
    title: '音频策略',
    fields: [
      { key: 'noiseGate', label: '噪声门限', value: '-45 dB' },
      { key: 'ttsVoice', label: '播报音色', value: '女声·清晰' },
      { key: 'ttsSpeed', label: '语速', value: '1.0x' }
    ]
  }
]

export function useSettingsPage() {
  return {
    settingSections
  }
}
