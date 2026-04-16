const logGroups = [
  {
    id: 'realtime',
    title: '实时日志',
    rows: [
      { time: '14:23:10', level: 'INFO', text: 'WebSocket 连接已建立，课堂流转录启动。' },
      { time: '14:23:28', level: 'INFO', text: '检测到提问窗口，已写入问题队列。' },
      { time: '14:24:11', level: 'WARN', text: '麦克风能量波动较大，已自动平滑增益。' },
      { time: '14:24:35', level: 'INFO', text: 'TTS 合成成功，播报队列长度 1。' }
    ]
  },
  {
    id: 'system',
    title: '系统事件',
    rows: [
      { time: '14:20:02', level: 'INFO', text: '课堂上下文快照已刷新（5s 周期）。' },
      { time: '14:19:48', level: 'INFO', text: '数据库写入成功，transcripts +12。' },
      { time: '14:19:06', level: 'ERROR', text: '外部模型接口延迟升高，已切换重试策略。' }
    ]
  }
]

export function useLogsPage() {
  return {
    logGroups
  }
}
