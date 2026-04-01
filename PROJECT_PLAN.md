# 项目总体规划（课堂模拟学生提问助手）

## 定位与主流程
- 本应用是“课堂模拟学生提问助手”，根据老师讲授内容实时生成并以语音方式提出学生问题，模拟课堂互动。
- 最小闭环数据流：实时音频 → 讲解文字 → 生成提问 → 语音提问
- 主流程步骤：实时音频输入、语音转写为讲解文字、基于最新讲解片段生成提问、语音播报提问

## 原则与约束
- 实时性优先级最高，所有实现必须服务于实时性。
- 任何扩展功能不得影响主流程的稳定性与连续性。
- 非核心功能必须满足：不阻塞主流程、不增加不可控时延、可异步或降级处理。

## 技术栈
- 编程语言：Python
- 后端框架：FastAPI
- ASGI服务器：Uvicorn
- 数据库：SQLite（当前阶段）
- ORM（数据库抽象层）：SQLModel
- 前端框架：Vue
- 桌面应用封装：Tauri

## 数据存储
- 目标：将所有可记录内容与指标持久化，便于统计、后续分析、数据利用。
- 数据范围：课程信息、课堂信息、转写内容、提问问题、评估指标、运行指标。
- 存储策略：优先本地轻量化存储，如 SQLite。
- 数据结构：课程 → 课堂 → 课堂内所有记录（转写、问题、评估指标、运行指标），按层级聚合与关联。

### 数据库设计
```SQL
-- =========================
-- sessions（课堂）
-- =========================
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    start_time DATETIME,
    end_time DATETIME,

    config TEXT,    -- JSON：运行配置信息

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- transcripts（转写分段）
-- =========================
CREATE TABLE transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    seq INTEGER,

    text TEXT NOT NULL,
    start_time REAL,   -- 秒
    end_time REAL,     -- 秒

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
CREATE INDEX idx_transcripts_session ON transcripts(session_id);
CREATE INDEX idx_transcripts_time ON transcripts(session_id, start_time);


-- =========================
-- questions（问题）
-- =========================
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,

    text TEXT NOT NULL,

    status TEXT,        -- generated / asked
    score REAL,         -- 质量/优先级评分

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    asked_at DATETIME,

    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
CREATE INDEX idx_questions_session ON questions(session_id);
CREATE INDEX idx_questions_status ON questions(status);


-- =========================
-- question_transcript_map（问题-上下文映射）
-- =========================
CREATE TABLE question_transcript_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    transcript_id INTEGER NOT NULL,

    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
);
CREATE INDEX idx_qt_question ON question_transcript_map(question_id);
CREATE INDEX idx_qt_transcript ON question_transcript_map(transcript_id);


-- =========================
-- segment_summaries（分段小结）
-- =========================
CREATE TABLE segment_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,

    text TEXT NOT NULL,
    start_time REAL,
    end_time REAL,

    score REAL,        -- 质量评分

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
CREATE INDEX idx_seg_sum_session ON segment_summaries(session_id);
CREATE INDEX idx_seg_sum_time ON segment_summaries(session_id, start_time);


-- =========================
-- segment_summary_transcript_map（小结-转写映射）
-- =========================
CREATE TABLE segment_summary_transcript_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    segment_summary_id INTEGER NOT NULL,
    transcript_id INTEGER NOT NULL,

    FOREIGN KEY (segment_summary_id) REFERENCES segment_summaries(id),
    FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
);
CREATE INDEX idx_seg_sum_map_summary ON segment_summary_transcript_map(segment_summary_id);
CREATE INDEX idx_seg_sum_map_transcript ON segment_summary_transcript_map(transcript_id);


-- =========================
-- llm_infos（LLM 模型价格信息）
-- =========================
CREATE TABLE llm_infos (
    name TEXT PRIMARY KEY NOT NULL,

    input REAL,
    output REAL,
    cache_read REAL,
    cache_write REAL
);


-- =========================
-- relay_logs（请求日志）
-- =========================
CREATE TABLE relay_logs (
    id INTEGER PRIMARY KEY,

    time INTEGER,
    request_model_name TEXT,
    request_api_key_name TEXT,
    channel_id INTEGER,
    channel_name TEXT,
    actual_model_name TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    ftut INTEGER,
    use_time INTEGER,
    cost REAL,
    request_content TEXT,
    response_content TEXT,
    error TEXT,
    attempts TEXT,
    total_attempts INTEGER
);


-- =========================
-- stats_totals（全量累计统计）
-- =========================
CREATE TABLE stats_totals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    input_token BIGINT,
    output_token BIGINT,
    input_cost REAL,
    output_cost REAL,
    wait_time BIGINT,
    request_success BIGINT,
    request_failed BIGINT
);


-- =========================
-- stats_dailies（按日统计）
-- =========================
CREATE TABLE stats_dailies (
    date TEXT PRIMARY KEY,

    input_token BIGINT,
    output_token BIGINT,
    input_cost REAL,
    output_cost REAL,
    wait_time BIGINT,
    request_success BIGINT,
    request_failed BIGINT
);


-- =========================
-- stats_hourlies（按小时统计）
-- =========================
CREATE TABLE stats_hourlies (
    hour INTEGER PRIMARY KEY AUTOINCREMENT,

    date TEXT NOT NULL,
    input_token BIGINT,
    output_token BIGINT,
    input_cost REAL,
    output_cost REAL,
    wait_time BIGINT,
    request_success BIGINT,
    request_failed BIGINT
);


-- =========================
-- settings（系统设置键值对）
-- =========================
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);


-- =========================
-- migration_records（数据库迁移版本记录）
-- =========================
CREATE TABLE migration_records (
    version INTEGER PRIMARY KEY AUTOINCREMENT,
    status INTEGER
);
```

## 扩展功能
- 数据可视化
  - 提供简单日志/各种指标统计视图，便于回看与调参。
  - 实现技术：SQLite 数据统计查询、简单图表库（如 Chart.js / ECharts / matplotlib）。
  - 流程简述：系统从数据库中读取课堂记录、提问数量、提问时间间隔等运行数据，通过统计分析生成图表或日志视图，用于展示课堂互动情况与系统运行指标。
- 关键词与知识点追踪
  - 从课堂转写内容中提取关键词与核心知识点，并统计其出现频率与覆盖情况，用于分析课程重点。
  - 实现技术：关键词提取算法（如 TF-IDF、KeyBERT）或基于大语言模型的关键词抽取。
  - 流程简述：系统对课堂转写文本进行分段处理，从中提取关键词与核心概念，并统计其出现频率，形成关键词列表和简单统计结果，用于辅助识别课堂重点内容。
- 课后报告生成
  - 在课堂结束后，系统自动整理课堂相关数据并生成课后报告 PDF。报告内容可包括课堂讲解摘要、提问记录、关键词与知识点统计以及课堂互动情况等等，用于回顾课堂过程并进行简单分析。
  - 实现技术：文本摘要生成（LLM 或摘要算法）、PDF 生成工具（如 reportlab 或 HTML 转 PDF）。
  - 流程简述：课堂结束后系统汇总课堂转写、提问记录与统计数据，生成课堂摘要与统计信息，并按照预设模板整合为结构化报告，最终导出为 PDF 文件。
- 课堂内容速览
  - 基于实时转写内容生成简要小结，并按照时间窗口滚动更新，帮助快速回顾课堂讲解脉络。
  - 实现技术：文本摘要模型或大语言模型（LLM）生成摘要。
  - 流程简述：系统按固定时间窗口（如几分钟）收集最近的转写内容，通过摘要模型生成简短小结，并持续更新课堂内容速览，形成对课堂讲解过程的动态概括。
- 课堂小测生成
  - 根据课堂转写内容自动生成简单的小测题目，围绕关键知识点设计选择题或简答题，用于检测对课堂内容的理解情况，并作为课堂阶段性回顾。
  - 实现技术：大语言模型（LLM）题目生成、简单题目模板。
  - 流程简述：系统从课堂转写内容中提取关键知识点，通过预设提示词生成选择题或简答题，并输出题目与参考答案，用于课堂阶段性测验或课后复习。
- 课堂提问质量分析
  - 对问题质量打分/分级，输出改进建议（离线或低优先级执行）。
  - 实现技术：大语言模型（LLM）评估、简单评分规则。
  - 流程简述：系统对已生成的问题进行离线分析，从清晰度、相关性和思考价值等维度进行评分，并生成简要评价与改进建议，用于优化后续提问策略。
- 课堂理解难点提示
  - 系统根据讲解内容和生成的问题，识别可能的理解难点或复杂概念，标记出课堂中信息密度较高或概念集中的片段，帮助分析哪些部分可能更容易引发学生疑问。
  - 实现技术：关键词密度分析、大语言模型语义分析。
  - 流程简述：系统结合课堂转写内容、关键词分布以及提问记录，对文本片段进行分析，识别概念密集或解释复杂的部分，并标记为可能的理解难点。
- 提问节奏调节
  - 根据课堂讲解节奏动态调整提问频率、难度与表达方式，使互动更加自然。
  - 实现技术：规则策略或简单节奏控制算法，大语言模型生成不同难度的问题。
  - 流程简述：系统根据讲解时间长度、最近提问时间以及内容变化情况判断是否需要生成新问题，并通过规则或策略动态调整提问频率与问题难度，以保持课堂互动节奏的自然性。

## 项目目录
```
OpenClass/
├── backend/                 # Python 后端
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── core/            # 核心业务
│   │   ├── api/             # 接口层
│   │   │   ├── routes/
│   │   │   └── deps.py      # 依赖注入
│   │   ├── db/              # 数据库
│   │   │   ├── session.py   # DB连接
│   │   │   ├── models.py    # SQLModel模型
│   │   │   └── crud/        # 数据操作
│   │   ├── services/        # 外部能力
│   │   │   ├── llm.py       # LLM调用
│   │   │   ├── asr.py       # 语音识别
│   │   │   └── tts.py       # 语音合成
│   │   ├── config.py        # 配置
│   │   └── utils/           # 工具函数
│   └── requirements.txt
├── frontend/                # Vue 前端
│   ├── src/
│   ├── index.html
│   └── package.json
├── tauri/                   # 桌面应用封装
├── data/                    # 本地数据
├── scripts/                 # 放一次性 / 工具型 / 运维型的代码
└── README.md
```