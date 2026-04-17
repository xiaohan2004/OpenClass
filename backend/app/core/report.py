"""课堂还原报告生成器。"""

from __future__ import annotations

import logging
import re
from functools import partial
from typing import Callable

from app.services.llm import generate_with_prompt

logger = logging.getLogger(__name__)


class ReportProcessor:
    """课堂还原报告处理器，提供直接调用入口。"""

    def __init__(self, agent: LectureReportAgent | None = None):
        self._agent = agent or create_default_lecture_report_agent()

    def generate_report(self, material: str, max_iters: int = 1) -> str:
        """根据课堂材料生成最终 HTML 报告。"""
        return self._agent.run(material=material, max_iters=max_iters)


class LectureReportAgent:
    """课堂还原报告 Agent（Plan + ReAct + Reflexion + HTML）。"""

    def __init__(self, llm_callable: Callable[[str], str]):
        self.llm = llm_callable

    def organize_material(self, material: str) -> str:
        prompt = f"""
你将获得课堂相关材料（转写/笔记/摘要）。

任务：
整理内容，但必须忠实原意。

要求：
- 保留所有关键信息
- 去除重复/噪声
- 按主题初步分类
- 不允许编造或扩展

材料：
{material}
"""
        return self.llm(prompt)

    def make_plan(self, organized: str) -> list[str]:
        prompt = f"""
你是一名大学教师。

请基于以下课堂内容设计报告结构：

{organized}

要求：
- 引言 + 多个主题 + 总结
- 结构清晰、逻辑递进
- 反映课堂讲解顺序
- 让未听课者也能理解

输出编号结构：
"""
        result = self.llm(prompt)
        return self.parse_steps(result)

    def execute_step(self, step: str, context: str, source: str) -> str:
        prompt = f"""
你正在撰写课堂报告。

当前部分：
{step}

已有内容：
{context}

课堂材料：
{source}

要求：
- 基于课堂内容（不得编造）
- 可适度解释帮助理解
- 保留“讲课感”
- 内容详细、清晰

输出该部分正文：
"""
        return self.llm(prompt)

    def check_faithfulness(self, report: str, source: str) -> str:
        prompt = f"""
请检查报告是否忠实于课堂：

课堂材料：
{source}

报告：
{report}

检查：
- 是否偏离原意
- 是否编造内容
- 是否遗漏重点

给出具体修改建议（必须具体）。
"""
        return self.llm(prompt)

    def improve_content(self, report: str) -> str:
        prompt = f"""
请优化课堂报告：

{report}

目标：
- 提升逻辑性
- 增强可读性
- 让未听课者理解
- 不改变原意

输出优化版本：
"""
        return self.llm(prompt)

    def to_html(self, report: str) -> str:
        prompt = f"""
请将以下内容转为HTML：

{report}

要求：
- 使用语义化标签（h1, h2, p, ul）
- 必须包含<style>
- 基础排版清晰

输出完整HTML：
"""
        return self.llm(prompt)

    def critique_html(self, html: str) -> str:
        prompt = f"""
请批评该HTML页面：

{html}

从以下角度：
- 美观性
- 可读性
- 层次结构
- 排版问题

必须具体指出问题。
"""
        return self.llm(prompt)

    def refine_html(self, html: str, feedback: str) -> str:
        prompt = f"""
根据反馈优化HTML：

原HTML：
{html}

反馈：
{feedback}

目标：
- 类似 Notion / Medium 风格
- 居中布局（max-width）
- 行距舒适
- 标题清晰
- 重点突出

限制：
- 不删除内容
- 不用外部库
- 使用内联CSS

输出最终HTML：
"""
        return self.llm(prompt)

    def run(self, material: str, max_iters: int = 1) -> str:
        """执行完整报告流程并返回最终 HTML。"""
        if not isinstance(material, str) or not material.strip():
            raise ValueError("material 不能为空")

        loops = max(0, int(max_iters))

        logger.info("开始整理课堂材料")
        organized = self.organize_material(material)

        logger.info("开始生成报告结构")
        plan = self.make_plan(organized)

        context = ""
        for step in plan:
            result = self.execute_step(step, context, organized).strip()
            if result:
                context = f"{context}\n{result}\n".strip()

        report = context
        for _ in range(loops):
            feedback = self.check_faithfulness(report, organized)
            report = self.llm(f"根据以下意见修改报告：\n{feedback}\n\n原文：\n{report}")

        report = self.improve_content(report)
        html = self.to_html(report)
        feedback = self.critique_html(html)
        return self.refine_html(html, feedback)

    def parse_steps(self, text: str) -> list[str]:
        """将模型输出结构化为步骤列表。"""
        steps: list[str] = []
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # 允许 1. / 1) / - / * 等序号或项目符号
            cleaned = re.sub(r"^\s*(?:\d+[\.)]\s*|[-*]\s*)", "", line).strip()
            if cleaned:
                steps.append(cleaned)

        return steps


def create_default_lecture_report_agent() -> LectureReportAgent:
    """创建使用默认课堂报告提示词的报告 Agent。"""
    llm_callable = partial(
        generate_with_prompt,
        system_prompt="你是课堂还原报告助手。输出必须忠于课堂材料，不得编造。",
    )
    return LectureReportAgent(llm_callable)
