# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path


def safe_filename(text, max_length=80):
    if not text:
        return "untitled"

    text = re.sub(r"[\r\n\t]", " ", text)
    text = re.sub(r"[#*!`$<>|:?/\\]", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fa5\- ]", "", text)
    text = re.sub(r"\s+", "_", text)

    return text[:max_length].strip("_") or "untitled"


def strip_h1(text):
    """移除正文中的一级标题"""
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).lstrip()
    return text


def extract_fragments(message):
    result = {"request": None, "response": None, "think": None}
    if not message:
        return result

    for frag in message.get("fragments", []):
        content = (frag.get("content") or "").strip()
        if not content:
            continue

        t = frag.get("type")
        if t == "REQUEST":
            result["request"] = content
        elif t == "THINK":
            result["think"] = content
        elif t == "RESPONSE":
            result["response"] = strip_h1(content)

    return result


def walk_main_chain(mapping):
    root = mapping.get("root")
    if not root or not root.get("children"):
        return

    node_id = root["children"][0]
    while node_id:
        node = mapping.get(node_id)
        if not node:
            break

        yield node
        children = node.get("children", [])
        node_id = children[0] if children else None


def quote_block(text):
    return "\n".join(f"> {line}" for line in text.splitlines())


def export_conversation(conv):
    mapping = conv.get("mapping", {})
    blocks = []

    for node in walk_main_chain(mapping):
        parts = extract_fragments(node.get("message"))

        if parts["request"]:
            blocks.append("## 👤 用户\n" + parts["request"])

        if parts["think"]:
            blocks.append(
                "## 🤖 DeepSeek（模型思考）\n" + quote_block(parts["think"])
            )

        if parts["response"]:
            blocks.append(
                "## 🤖 DeepSeek（最终回答）\n" + parts["response"]
            )

    return "\n\n".join(blocks).strip() + "\n"


def main():
    input_path = Path("conversations.json")
    output_dir = Path("deepseek_conversations")
    output_dir.mkdir(exist_ok=True)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError("JSON 顶层必须是 list")

    index_lines = ["# 导出会话索引\n"]

    for idx, conv in enumerate(data, start=1):
        md = export_conversation(conv)

        filename = safe_filename(conv.get("title")) or f"conversation_{idx}"
        md_name = f"{idx:03d}_{filename}.md"
        path = output_dir / md_name
        path.write_text(md, encoding="utf-8")

        index_lines.append(f"- [{md_name}]({md_name})")
        print(f"✔ 导出完成: {path}")

    # 生成 index.md
    index_path = output_dir / "index.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"✔ 索引生成: {index_path}")


if __name__ == "__main__":
    main()
