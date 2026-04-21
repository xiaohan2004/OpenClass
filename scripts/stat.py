import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = r"..\backend\data\openclass.db"

# =========================
# 读取数据
# =========================
conn = sqlite3.connect(DB_PATH)

query = """
SELECT service_type, latency
FROM relay_logs
WHERE service_type IN ('llm', 'tts', 'asr')
  AND latency IS NOT NULL
"""

df = pd.read_sql_query(query, conn)
conn.close()

# =========================
# 清洗数据
# =========================
df["latency"] = df["latency"].astype(float)

# =========================
# 过滤异常值（重点）
# 只看 0 ~ 5000 ms（你可以再调小）
# =========================
min_latency = 0
max_latency = 6000
df = df[(df["latency"] >= min_latency) & (df["latency"] <= max_latency)]

# =========================
# 分组
# =========================
groups = {}
stats_output = []

for t in ["llm", "tts", "asr"]:
    data = df[df["service_type"] == t]["latency"]
    groups[t] = data

    # ===== 控制台统计 =====
    if len(data) > 0:
        stats = {
            "type": t,
            "count": len(data),
            "mean": data.mean(),
            "median": data.median(),
            "p90": data.quantile(0.90),
            "p95": data.quantile(0.95),
            "max": data.max(),
            "min": data.min(),
        }
    else:
        stats = {
            "type": t,
            "count": 0
        }

    stats_output.append(stats)

# =========================
# 打印统计信息
# =========================
print(f"\n========== Latency Stats ({min_latency}~{max_latency}ms) ==========")
for s in stats_output:
    print(f"\n[{s['type']}]")
    for k, v in s.items():
        if k != "type":
            print(f"  {k}: {v}")

# =========================
# 画图
# =========================
plt.figure(figsize=(10, 6))

bins = 40  # 稍微收紧一点

for t, data in groups.items():
    plt.hist(data, bins=bins, alpha=0.5, label=t, density=True)

plt.title(f"Latency Distribution (Filtered {min_latency}~{max_latency}ms)")
plt.xlabel("Latency (ms)")
plt.ylabel("Density")
plt.legend()
plt.grid(alpha=0.3)

plt.tight_layout()
plt.show()