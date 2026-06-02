import argparse
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "data" / "openclass.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="统计 questions 表中的分数分布，并可视化展示。"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="SQLite 数据库路径，默认指向 backend/data/openclass.db",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=20,
        help="分箱数量参数。当前区间柱状图使用固定分数区间，因此该参数主要保留兼容。",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=-1.0,
        help="统计和绘图的最小分数，默认 -1.0",
    )
    parser.add_argument(
        "--max-score",
        type=float,
        default=1.0,
        help="统计和绘图的最大分数，默认 1.0",
    )
    return parser.parse_args()


def load_question_scores(db_path: Path) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        query = """
        SELECT id, session_id, text, status, score, created_at, asked_at
        FROM questions
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def print_console_stats(
    df: pd.DataFrame,
    min_score: float,
    max_score: float,
    bins: int,
) -> None:
    total_count = len(df)
    scored_df = df[df["score"].notna()].copy()
    scored_count = len(scored_df)
    missing_count = total_count - scored_count

    print("\n========== Question Score Stats ==========")
    print(f"总问题数: {total_count}")
    print(f"已评分问题数: {scored_count}")
    print(f"未评分问题数: {missing_count}")

    if scored_count == 0:
        print("没有可统计的分数数据。")
        return

    scored_df["score"] = scored_df["score"].astype(float)
    scores = scored_df["score"]

    print("\n========== Score Summary ==========")
    print(f"min: {scores.min():.3f}")
    print(f"max: {scores.max():.3f}")
    print(f"mean: {scores.mean():.3f}")
    print(f"median: {scores.median():.3f}")
    print(f"std: {scores.std(ddof=0):.3f}")
    print(f"p25: {scores.quantile(0.25):.3f}")
    print(f"p75: {scores.quantile(0.75):.3f}")
    print(f"p90: {scores.quantile(0.90):.3f}")
    print(f"p95: {scores.quantile(0.95):.3f}")

    clipped_scores = scores[(scores >= min_score) & (scores <= max_score)]

    print(
        f"\n========== Binned Distribution ({min_score}~{max_score}, bins={bins}) =========="
    )

    if clipped_scores.empty:
        print("没有落在指定区间内的分数。")
        return

    intervals = pd.cut(
        clipped_scores,
        bins=bins,
        include_lowest=True,
        right=True,
    )
    distribution = intervals.value_counts().sort_index()

    for interval, count in distribution.items():
        ratio = count / len(clipped_scores) * 100
        print(f"{interval}: {count} ({ratio:.2f}%)")

    print("\n========== Highest / Lowest Scores ==========")

    lowest = scored_df.nsmallest(5, "score")[["id", "score", "text"]]
    highest = scored_df.nlargest(5, "score")[["id", "score", "text"]]

    print("\n[最低 5 条]")
    for _, row in lowest.iterrows():
        print(
            f"  id={row['id']} "
            f"score={row['score']:.3f} "
            f"text={str(row['text'])[:80]}"
        )

    print("\n[最高 5 条]")
    for _, row in highest.iterrows():
        print(
            f"  id={row['id']} "
            f"score={row['score']:.3f} "
            f"text={str(row['text'])[:80]}"
        )


def plot_score_distribution(
    df: pd.DataFrame,
    min_score: float,
    max_score: float,
    bins: int,
) -> None:
    scored_df = df[df["score"].notna()].copy()

    if scored_df.empty:
        print("没有可绘制的分数数据。")
        return

    scored_df["score"] = scored_df["score"].astype(float)
    scores = scored_df["score"]

    clipped_scores = scores[(scores >= min_score) & (scores <= max_score)]

    if clipped_scores.empty:
        print("没有落在指定区间内的分数，跳过绘图。")
        return

    bin_edges = [
        -1.0,
        -0.8,
        -0.6,
        -0.4,
        -0.2,
        0.0,
        0.2,
        0.4,
        0.6,
        0.8,
        0.9,
        1.0,
    ]

    bin_labels = [
        "-1.0~-0.8",
        "-0.8~-0.6",
        "-0.6~-0.4",
        "-0.4~-0.2",
        "-0.2~0.0",
        "0.0~0.2",
        "0.2~0.4",
        "0.4~0.6",
        "0.6~0.8",
        "0.8~0.9",
        "0.9~1.0",
    ]

    intervals = pd.cut(
        clipped_scores,
        bins=bin_edges,
        labels=bin_labels,
        include_lowest=True,
        right=True,
    )

    counts = intervals.value_counts().sort_index()
    ratios = counts / counts.sum() * 100

    fig, ax = plt.subplots(figsize=(11, 5))

    bars = ax.bar(
        counts.index.astype(str),
        ratios.values,
        edgecolor="black",
        alpha=0.85,
    )

    ax.set_title("Score Distribution of Generated Questions", fontsize=14)
    ax.set_xlabel("Score Range")
    ax.set_ylabel("Proportion (%)")
    ax.set_ylim(0, max(ratios.values) * 1.15)

    ax.grid(axis="y", alpha=0.25)

    for bar, ratio, count in zip(bars, ratios.values, counts.values):
        if count > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{ratio:.1f}%\n({count})",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()


def main() -> None:
    args = parse_args()
    db_path = args.db_path.expanduser().resolve()

    if not db_path.exists():
        raise FileNotFoundError(f"数据库文件不存在: {db_path}")

    df = load_question_scores(db_path)

    print_console_stats(
        df=df,
        min_score=args.min_score,
        max_score=args.max_score,
        bins=args.bins,
    )

    plot_score_distribution(
        df=df,
        min_score=args.min_score,
        max_score=args.max_score,
        bins=args.bins,
    )

    plt.show()


if __name__ == "__main__":
    main()