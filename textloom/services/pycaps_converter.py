#!/usr/bin/env python3
"""
SRT字幕文件转换为PyCaps JSON格式的转换器
将SRT文件转换为PyCaps --subtitle-data 参数所需的JSON格式
"""

import json
import re
import sys
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TimeFragment:
    start: float
    end: float
    
    def to_dict(self) -> Dict[str, float]:
        return {"start": self.start, "end": self.end}


@dataclass
class Size:
    width: int = 0
    height: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {"width": self.width, "height": self.height}


@dataclass
class Position:
    x: int = 0
    y: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass
class ElementLayout:
    position: Position
    size: Size
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position.to_dict(),
            "size": self.size.to_dict()
        }


def parse_srt_time(time_str: str) -> float:
    """将SRT时间格式转换为秒数"""
    # SRT格式: 00:00:01,500 -> 1.5秒
    time_str = time_str.strip()
    if ',' in time_str:
        time_str = time_str.replace(',', '.')
    
    parts = time_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid time format: {time_str}")
    
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    
    return hours * 3600 + minutes * 60 + seconds


def split_text_to_words(text: str, start_time: float, end_time: float) -> List[Dict[str, Any]]:
    """将文本按词分割并分配时间戳"""
    # 清理文本
    text = text.strip()
    if not text:
        return []
    
    # 按空格分词
    words = text.split()
    if not words:
        return []
    
    # 计算总持续时间
    total_duration = end_time - start_time
    
    # 简单的均匀时间分配策略
    # 考虑每个词的长度权重
    word_lengths = [len(word) for word in words]
    total_length = sum(word_lengths)
    
    result_words = []
    current_time = start_time
    
    for i, word in enumerate(words):
        # 基于词长度按比例分配时间
        if total_length > 0:
            word_duration = total_duration * (word_lengths[i] / total_length)
        else:
            word_duration = total_duration / len(words)
        
        word_end_time = current_time + word_duration
        
        # 确保最后一个词结束时间正确
        if i == len(words) - 1:
            word_end_time = end_time
        
        word_data = {
            "clips": [],
            "text": word,
            "semantic_tags": [],
            "structure_tags": [],
            "max_layout": ElementLayout(Position(), Size()).to_dict(),
            "time": TimeFragment(current_time, word_end_time).to_dict()
        }
        
        result_words.append(word_data)
        current_time = word_end_time
    
    return result_words


def parse_srt_file(srt_path: str) -> Dict[str, Any]:
    """解析SRT文件并转换为PyCaps JSON格式"""
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # 分割SRT条目
    entries = re.split(r'\n\s*\n', content)
    
    segments = []
    
    for entry in entries:
        if not entry.strip():
            continue
        
        lines = entry.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # 解析序号（第一行）
        try:
            subtitle_id = int(lines[0])
        except ValueError:
            continue
        
        # 解析时间（第二行）
        time_line = lines[1]
        time_match = re.match(r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})', time_line)
        if not time_match:
            continue
        
        start_time = parse_srt_time(time_match.group(1))
        end_time = parse_srt_time(time_match.group(2))
        
        # 解析字幕文本（第三行及之后）
        subtitle_text = '\n'.join(lines[2:])
        
        # 创建词级数据
        words = split_text_to_words(subtitle_text, start_time, end_time)
        
        if not words:
            continue
        
        # 创建Line对象
        line_data = {
            "words": words,
            "structure_tags": [],
            "max_layout": ElementLayout(Position(), Size()).to_dict(),
            "time": TimeFragment(start_time, end_time).to_dict()
        }
        
        # 创建Segment对象
        segment_data = {
            "lines": [line_data],
            "structure_tags": [],
            "max_layout": ElementLayout(Position(), Size()).to_dict(),
            "time": TimeFragment(start_time, end_time).to_dict()
        }
        
        segments.append(segment_data)
    
    # 创建Document对象
    document = {
        "segments": segments
    }
    
    return document


def convert_srt_to_pycaps_json(srt_file: str, output_file: str = None) -> str:
    """转换SRT文件为PyCaps JSON格式"""
    
    srt_path = Path(srt_file)
    if not srt_path.exists():
        raise FileNotFoundError(f"SRT file not found: {srt_file}")
    
    if output_file is None:
        output_file = str(srt_path.with_suffix('.json'))
    
    print(f"Converting {srt_file} to PyCaps JSON format...")
    
    # 解析并转换
    json_data = parse_srt_file(str(srt_path))
    
    # 保存JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"Conversion completed: {output_file}")
    print(f"Generated {len(json_data['segments'])} segments with word-level timing")
    
    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python srt_to_pycaps_json.py <srt_file> [output_json_file]")
        sys.exit(1)
    
    srt_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result_file = convert_srt_to_pycaps_json(srt_file, output_file)
        print(f"✅ Success! JSON file saved to: {result_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)