"""运行时离线演示件：MockLLM（测试与 LLM_MODE=mock 共用，无 Key 无网可跑）。

分流标记：system 提示里的角色名（学习规划/辅导/评估代理）。
响应文本严格满足 agents.py 三个解析器的 tag 格式。
"""

from __future__ import annotations

import re


class _Block:
    type = "text"  # _extract_text 按 block.type == "text" 过滤，缺了会被整块丢弃

    def __init__(self, text: str) -> None:
        self.text = text


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.usage = _Usage(input_tokens=50, output_tokens=20)


class MockLLM:
    """按 system 里的角色标记分流；固定用量（50 in / 20 out）保证成本可断言。"""

    def create(self, *, model: str, max_tokens: int, system: str, messages: list):
        if "学习规划代理" in system:
            return _Response(self._plan_text())
        if "学习辅导代理" in system:
            return _Response(self._lesson_text(system, messages))
        if "学习评估代理" in system:
            return _Response(self._eval_text())
        raise ValueError(f"MockLLM 无法识别的角色提示: {system[:40]}")

    def _plan_text(self) -> str:
        return (
            "<rationale>从定义到几何直观再到运算法则，符合认知递进</rationale>\n"
            "<step>导数的定义与记号</step>\n"
            "<step>导数的几何意义与切线</step>\n"
            "<step>基本求导法则</step>"
        )

    def _lesson_text(self, system: str, messages: list) -> str:
        step = "该步骤"
        if messages:
            m = re.search(r"请讲解这一步：(.*)", str(messages[0].get("content", "")))
            if m:
                step = m.group(1).strip()
        content = (
            f"关于「{step}」的讲解：我们先从直观入手，再用严格定义收束。\n\n"
            f"把「{step}」放到整个学习路径里，它承接上一步的结论，"
            "也为后续法则的应用铺路。记住这里的推导链条，比背结论更重要。"
        )
        keypoints = f"「{step}」的核心直观；推导链条的每一步为什么成立；常见误解与自查方法"
        return f"<content>{content}</content>\n<keypoints>{keypoints}</keypoints>"

    def _eval_text(self) -> str:
        return (
            "<score>78</score>\n"
            "<strengths>定义部分理解扎实；能复述推导链条</strengths>\n"
            "<gaps>几何直观还需强化；法则综合运用不熟练</gaps>\n"
            "<recommendation>下一步用图像题巩固几何意义，再做两道法则综合题</recommendation>"
        )
