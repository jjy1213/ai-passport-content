"""Ask Qwen to review the four 20-word courses; save findings for editorial review."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEMES = ("good-morning", "animal-friends", "snack-time", "story-trip")


def main() -> None:
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise SystemExit("Set DASHSCOPE_API_KEY in your local environment first")

    from dashscope import Generation

    findings = {}
    for theme in THEMES:
        course = json.loads((ROOT / "courses" / "v2" / f"{theme}.json").read_text(encoding="utf-8"))
        prompt = (
            "请检查这份儿童英语课程 JSON。逐条核对英文词义、英文例句是否自然且真正使用目标词、"
            "中文释义和例句翻译是否准确、是否适合小学儿童。不需要为了润色而改动正确内容。"
            "只输出 JSON 对象，格式为 {\"issues\":[{\"word\":\"...\",\"field\":\"...\","
            "\"reason\":\"...\",\"suggestion\":\"...\"}]}。无问题时 issues 为空数组。\n"
            + json.dumps(course, ensure_ascii=False)
        )
        result = Generation.call(
            api_key=key,
            model="qwen-plus",
            messages=[{"role": "user", "content": prompt}],
            result_format="message",
            response_format={"type": "json_object"},
        )
        if result.status_code != 200:
            raise RuntimeError(f"Qwen review failed for {theme}: HTTP {result.status_code}")
        review = json.loads(result.output.choices[0].message.content)
        if not isinstance(review.get("issues"), list):
            raise RuntimeError(f"Unexpected Qwen review shape for {theme}")
        findings[theme] = review["issues"]
        print(f"{theme}: {len(review['issues'])} suggested issues")

    output = ROOT / "tmp" / "qwen-course-review.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Review report saved to {output}")


if __name__ == "__main__":
    main()
