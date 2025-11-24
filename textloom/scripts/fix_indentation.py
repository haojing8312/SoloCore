#!/usr/bin/env python3
"""
修复日志转换后的缩进问题
"""

import re
from pathlib import Path


def fix_file_indentation(file_path: Path):
    """修复单个文件的缩进"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for i, line in enumerate(lines):
        # 查找需要缩进的log调用
        if re.match(r"^log_(debug|info|warning|error|critical)\(", line.strip()):
            # 查找上一个非空行的缩进
            prev_indent = ""
            for j in range(i - 1, -1, -1):
                prev_line = lines[j]
                if prev_line.strip():
                    prev_indent = prev_line[: len(prev_line) - len(prev_line.lstrip())]
                    break

            # 如果上一行有缩进，应用相同的缩进
            if prev_indent:
                new_lines.append(prev_indent + line.strip() + "\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"修复了 {file_path}")


if __name__ == "__main__":
    # 修复已转换的文件
    files_to_fix = [
        Path("scripts/create_superuser.py"),
        Path("scripts/db_connection_optimizer.py"),
    ]

    for file_path in files_to_fix:
        if file_path.exists():
            fix_file_indentation(file_path)
        else:
            print(f"文件不存在: {file_path}")
