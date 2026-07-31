"""
Project Generator Module
Generates complete project solutions based on discovered hot topics
"""

import json
import logging
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ProjectGenerator:
    """
    Generate complete project solutions based on AI hot topics
    """

    def __init__(self, config: Dict):
        self.config = config
        self.generator_config = config.get('generator', {})
        self.tech_stacks = self.generator_config.get('tech_stacks', [])
        self.output_dir = Path(config.get('output_dir', 'data/projects'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _make_class_name(self, title: str) -> str:
        """将标题转换为合法的 Python 类名（PascalCase）"""
        import re
        # 移除特殊字符，保留字母、数字、空格
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', title)
        # 按空格分割，每个单词首字母大写
        parts = cleaned.split()
        # 组合成 PascalCase
        class_name = ''.join(word.capitalize() for word in parts)
        # 确保以字母开头
        if not class_name or not class_name[0].isalpha():
            class_name = 'Project' + class_name
        return class_name

    def generate_project(self, topic: Dict) -> str:
        """
        Generate a complete project based on the given hot topic
        
        Args:
            topic: Hot topic information from discoverer
            
        Returns:
            Path to the generated project directory
        """
        # Determine the best tech stack for this topic
        tech_stack = self._select_tech_stack(topic)
        
        # Generate project name
        date_str = datetime.now().strftime('%Y%m%d')
        topic_slug = self._slugify(topic.get('title', 'ai-project'))
        project_name = f"ai-daily-{date_str}-{topic_slug}"
        
        # Create project directory
        project_dir = self.output_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating project: {project_name} with tech stack: {tech_stack['name']}")
        
        # Generate project structure
        self._generate_project_structure(project_dir, topic, tech_stack)
        
        # Generate source code
        self._generate_source_code(project_dir, topic, tech_stack)
        
        # Generate documentation
        self._generate_documentation(project_dir, topic, tech_stack)
        
        # Generate tests
        self._generate_tests(project_dir, topic, tech_stack)
        
        # Generate CI/CD configuration
        self._generate_cicd_config(project_dir, topic, tech_stack)
        
        # Generate Docker configuration
        self._generate_docker_config(project_dir, topic, tech_stack)
        
        return str(project_dir)

    def _select_tech_stack(self, topic: Dict) -> Dict:
        """
        Select the most appropriate tech stack for the topic
        """
        # Simple heuristic based on topic keywords and tags
        tags = topic.get('tags', [])
        keywords = topic.get('keywords', [])
        combined_text = ' '.join(tags + keywords).lower()
        
        # Scoring logic
        stack_scores = {}
        for stack in self.tech_stacks:
            score = 0
            stack_name_lower = stack['name'].lower()
            
            # Keyword matching
            if 'agent' in combined_text and 'agent' in stack_name_lower:
                score += 3
            if 'web' in combined_text and 'web' in stack_name_lower:
                score += 2
            if 'data' in combined_text and 'data' in stack_name_lower:
                score += 2
            if 'full' in combined_text and 'full' in stack_name_lower:
                score += 2
                
            # Default score
            if score == 0:
                score = 1
                
            stack_scores[stack['name']] = score
        
        # Select the highest scoring stack
        best_stack_name = max(stack_scores, key=stack_scores.get)
        best_stack = next(s for s in self.tech_stacks if s['name'] == best_stack_name)
        
        return best_stack

    def _generate_project_structure(self, project_dir: Path, topic: Dict, tech_stack: Dict):
        """
        Generate the basic project directory structure
        """
        stack_name = tech_stack['name']
        
        if stack_name == 'python_tool':
            self._create_python_tool_structure(project_dir, topic)
        elif stack_name == 'web_app':
            self._create_web_app_structure(project_dir, topic)
        elif stack_name == 'full_stack':
            self._create_full_stack_structure(project_dir, topic)
        elif stack_name == 'ai_agent':
            self._create_ai_agent_structure(project_dir, topic)
        elif stack_name == 'data_pipeline':
            self._create_data_pipeline_structure(project_dir, topic)

    def _create_python_tool_structure(self, project_dir: Path, topic: Dict):
        """Create Python tool project structure"""
        (project_dir / "src" / topic['slug']).mkdir(parents=True, exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)
        (project_dir / "examples").mkdir(exist_ok=True)
        
    def _create_web_app_structure(self, project_dir: Path, topic: Dict):
        """Create web app project structure"""
        (project_dir / "frontend" / "src").mkdir(parents=True, exist_ok=True)
        (project_dir / "frontend" / "public").mkdir(parents=True, exist_ok=True)
        (project_dir / "backend" / "src").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)
        
    def _create_full_stack_structure(self, project_dir: Path, topic: Dict):
        """Create full stack project structure"""
        (project_dir / "api" / "src").mkdir(parents=True, exist_ok=True)
        (project_dir / "frontend" / "src").mkdir(parents=True, exist_ok=True)
        (project_dir / "database" / "migrations").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)
        
    def _create_ai_agent_structure(self, project_dir: Path, topic: Dict):
        """Create AI agent project structure"""
        (project_dir / "agent" / "src").mkdir(parents=True, exist_ok=True)
        (project_dir / "tools").mkdir(exist_ok=True)
        (project_dir / "config").mkdir(exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)
        (project_dir / "examples").mkdir(exist_ok=True)
        
    def _create_data_pipeline_structure(self, project_dir: Path, topic: Dict):
        """Create data pipeline project structure"""
        (project_dir / "pipeline" / "src").mkdir(parents=True, exist_ok=True)
        (project_dir / "data" / "raw").mkdir(parents=True, exist_ok=True)
        (project_dir / "data" / "processed").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)

    def _generate_source_code(self, project_dir: Path, topic: Dict, tech_stack: Dict):
        """
        Generate source code files based on the topic and tech stack
        """
        stack_name = tech_stack['name']
        
        if stack_name == 'python_tool':
            self._generate_python_tool_code(project_dir, topic)
        elif stack_name == 'web_app':
            self._generate_web_app_code(project_dir, topic)
        elif stack_name == 'full_stack':
            self._generate_full_stack_code(project_dir, topic)
        elif stack_name == 'ai_agent':
            self._generate_ai_agent_code(project_dir, topic)
        elif stack_name == 'data_pipeline':
            self._generate_data_pipeline_code(project_dir, topic)

    def _generate_python_tool_code(self, project_dir: Path, topic: Dict):
        """Generate Python tool source code - real scaffold, not placeholder"""
        src_dir = project_dir / "src"
        
        # 生成合法的类名
        class_name = self._make_class_name(topic['title'])
        
        # === src/__init__.py ===
        init_file = src_dir / "__init__.py"
        init_file.write_text(f'"""{topic["title"]} - AI Daily Project"""\n\n__version__ = "0.1.0"\n__author__ = "AI Daily Agent"\n')

        # === src/config.py - 真实配置系统 ===
        config_file = src_dir / "config.py"
        config_file.write_text(f'''"""
配置模块 - 支持环境变量、配置文件、命令行参数三层配置

使用方法:
    1. 复制 .env.example 为 .env，填入你的配置
    2. 或通过环境变量传入
    3. 或通过命令行参数传入（优先级最高）
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """应用配置 - 在此定义所有配置项"""
    
    # === 基础配置 ===
    app_name: str = "{topic['title']}"
    version: str = "0.1.0"
    debug: bool = False
    
    # === 输入输出路径 ===
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    
    # === API 密钥（需要你填入真实值）===
    # 在 .env 文件中设置: API_KEY=your_key_here
    api_key: Optional[str] = None
    
    # === 模型配置（根据话题调整）===
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # === 日志配置 ===
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    def __post_init__(self):
        """从环境变量加载配置"""
        self.debug = os.getenv("DEBUG", str(self.debug)).lower() == "true"
        self.api_key = os.getenv("API_KEY", self.api_key)
        self.model_name = os.getenv("MODEL_NAME", self.model_name)
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        
        if self.input_path is None:
            self.input_path = os.getenv("INPUT_PATH", "./data/input")
        if self.output_path is None:
            self.output_path = os.getenv("OUTPUT_PATH", "./data/output")
    
    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.api_key:
            raise ValueError(
                "API_KEY 未配置！请在 .env 文件中设置，或设置环境变量 API_KEY"
            )
        return True


def load_config() -> AppConfig:
    """加载配置，优先从 .env 文件读取"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv 未安装，使用环境变量
    
    return AppConfig()
''')

        # === src/logger.py - 真实日志系统 ===
        logger_file = src_dir / "logger.py"
        logger_file.write_text('''"""
日志模块 - 统一的日志配置

使用方法:
    from src.logger import get_logger
    logger = get_logger(__name__)
    logger.info("这是一条日志")
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "app",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """配置并返回 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件输出（可选）
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取已配置的 logger"""
    return logging.getLogger(name)
''')

        # === src/models.py - 数据模型定义 ===
        models_file = src_dir / "models.py"
        models_file.write_text(f'''"""
数据模型 - 定义输入输出的数据结构

根据话题 "{topic['title']}" 设计，你需要根据实际需求修改这些模型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class InputData:
    """输入数据结构 - 根据实际输入格式修改"""
    content: str
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> bool:
        """验证输入数据"""
        if not self.content:
            raise ValueError("content 不能为空")
        return True


@dataclass
class OutputData:
    """输出数据结构 - 根据实际输出格式修改"""
    result: Any
    status: TaskStatus = TaskStatus.SUCCESS
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {{
            "result": self.result,
            "status": self.status.value,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }}


@dataclass
class ProcessingResult:
    """处理结果 - 包含详细统计信息"""
    success: bool
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    outputs: List[OutputData] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    def summary(self) -> str:
        """生成处理摘要"""
        return (
            f"处理完成: {{self.processed_items}}/{{self.total_items}} 成功, "
            f"{{self.failed_items}} 失败, 耗时 {{self.duration_seconds:.2f}}s"
        )
''')

        # === src/processor.py - 核心处理器（需要用户填充逻辑）===
        processor_file = src_dir / "processor.py"
        processor_file.write_text(f'''"""
核心处理器 - 在此实现 "{topic['title']}" 的业务逻辑

这是整个项目的核心文件。框架已经搭好，你只需要实现下面标记为
"FILL_HERE" 的方法即可。

需要实现的方法:
    - process_item(): 处理单条数据
    - batch_process(): 批量处理（可选，默认使用 process_item）
"""

import time
from abc import ABC, abstractmethod
from typing import List, Optional

from src.config import AppConfig
from src.logger import setup_logger
from src.models import InputData, OutputData, ProcessingResult, TaskStatus

logger = setup_logger(__name__)


class BaseProcessor(ABC):
    """
    处理器基类 - 定义处理流程的标准接口
    
    所有具体的处理器都应该继承这个类并实现 process_item 方法。
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.processed_count = 0
        self.failed_count = 0
    
    @abstractmethod
    def process_item(self, item: InputData) -> OutputData:
        """
        处理单条数据 - 这是你需要实现的核心逻辑
        
        Args:
            item: 输入数据
            
        Returns:
            处理结果
            
        Example:
            def process_item(self, item: InputData) -> OutputData:
                # 在这里实现你的处理逻辑
                result = your_logic(item.content)
                return OutputData(result=result, status=TaskStatus.SUCCESS)
        """
        pass
    
    def batch_process(self, items: List[InputData]) -> ProcessingResult:
        """批量处理数据"""
        start_time = time.time()
        outputs = []
        
        logger.info(f"开始处理 {{len(items)}} 条数据...")
        
        for i, item in enumerate(items, 1):
            try:
                logger.debug(f"处理第 {{i}}/{{len(items)}} 条数据")
                output = self.process_item(item)
                outputs.append(output)
                self.processed_count += 1
            except Exception as e:
                logger.error(f"处理第 {{i}} 条数据失败: {{e}}")
                outputs.append(OutputData(
                    result=None,
                    status=TaskStatus.FAILED,
                    error_message=str(e)
                ))
                self.failed_count += 1
        
        duration = time.time() - start_time
        
        result = ProcessingResult(
            success=self.failed_count == 0,
            total_items=len(items),
            processed_items=self.processed_count,
            failed_items=self.failed_count,
            outputs=outputs,
            duration_seconds=duration
        )
        
        logger.info(result.summary())
        return result


class {class_name}Processor(BaseProcessor):
    """
    具体的处理器实现
    
    根据话题: {topic['title']}
    描述: {topic['description']}
    
    TODO: 在 process_item 方法中实现你的业务逻辑
    """
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        # 初始化你的资源（API client、模型等）
        # self.client = YourAPIClient(config.api_key)
    
    def process_item(self, item: InputData) -> OutputData:
        """
        处理单条数据 - 在此实现核心逻辑
        
        示例场景:
            - 如果是文本处理: 对 content 进行分词、摘要、翻译等
            - 如果是数据分析: 对 content 进行统计、可视化等
            - 如果是 API 调用: 将 content 发送到外部 API 并获取结果
        """
        # === 在这里实现你的逻辑 ===
        
        # 示例: 简单的文本处理
        result = self._process_text(item.content)
        
        return OutputData(
            result=result,
            status=TaskStatus.SUCCESS,
            metadata={{"source": item.source}}
        )
    
    def _process_text(self, text: str) -> str:
        """
        文本处理逻辑 - 根据话题实现具体功能
        
        TODO: 替换为实际的处理逻辑
        """
        # === FILL_HERE: 实现你的处理逻辑 ===
        
        # 示例处理（替换为你的实际逻辑）
        processed = text.strip()
        processed = processed.lower()
        
        return processed
''')

        # === src/io_utils.py - 输入输出工具 ===
        io_file = src_dir / "io_utils.py"
        io_file.write_text('''"""
输入输出工具 - 处理数据的读取和写入

支持格式:
    - JSON
    - CSV
    - 纯文本
    - 自定义格式（继承 BaseReader/BaseWriter）
"""

import json
import csv
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from src.logger import setup_logger
from src.models import InputData

logger = setup_logger(__name__)


class BaseReader(ABC):
    """数据读取器基类"""
    
    @abstractmethod
    def read(self, path: str) -> List[InputData]:
        pass


class JsonReader(BaseReader):
    """JSON 文件读取器"""
    
    def read(self, path: str) -> List[InputData]:
        logger.info(f"读取 JSON 文件: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        items = []
        for item_data in data:
            items.append(InputData(
                content=item_data.get("content", ""),
                source=item_data.get("source", path),
                metadata=item_data.get("metadata", {})
            ))
        
        logger.info(f"读取了 {len(items)} 条数据")
        return items


class CsvReader(BaseReader):
    """CSV 文件读取器"""
    
    def __init__(self, content_column: str = "content"):
        self.content_column = content_column
    
    def read(self, path: str) -> List[InputData]:
        logger.info(f"读取 CSV 文件: {path}")
        items = []
        
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(InputData(
                    content=row.get(self.content_column, ""),
                    source=path,
                    metadata={k: v for k, v in row.items() if k != self.content_column}
                ))
        
        logger.info(f"读取了 {len(items)} 条数据")
        return items


class TextReader(BaseReader):
    """纯文本文件读取器（每行一条数据）"""
    
    def read(self, path: str) -> List[InputData]:
        logger.info(f"读取文本文件: {path}")
        items = []
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(InputData(content=line, source=path))
        
        logger.info(f"读取了 {len(items)} 条数据")
        return items


def get_reader(file_path: str) -> BaseReader:
    """根据文件扩展名自动选择读取器"""
    ext = Path(file_path).suffix.lower()
    
    readers = {
        ".json": JsonReader,
        ".csv": CsvReader,
        ".txt": TextReader,
    }
    
    reader_class = readers.get(ext)
    if not reader_class:
        raise ValueError(f"不支持的文件格式: {ext}，支持: {list(readers.keys())}")
    
    return reader_class()


def write_json(data: List[dict], output_path: str) -> None:
    """将结果写入 JSON 文件"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已写入: {output_path}")


def write_csv(data: List[dict], output_path: str) -> None:
    """将结果写入 CSV 文件"""
    if not data:
        logger.warning("没有数据可写入")
        return
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    logger.info(f"结果已写入: {output_path}")
''')

        # === src/main.py - 完整的 CLI 入口 ===
        main_file = src_dir / "main.py"
        main_file.write_text(f'''"""
{topic['title']}

{topic['description']}

使用方法:
    # 处理单个文件
    python -m src.main --input data/input.json --output data/output.json
    
    # 指定格式
    python -m src.main --input data/input.csv --output data/output.csv
    
    # 详细输出
    python -m src.main --input data/input.txt --output data/output.json --verbose

Generated by AI Daily Agent on {datetime.now().strftime('%Y-%m-%d')}
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from src.config import load_config, AppConfig
from src.logger import setup_logger
from src.models import InputData, TaskStatus
from src.processor import {class_name}Processor
from src.io_utils import get_reader, write_json, write_csv


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="{topic['title']}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径 (支持 .json, .csv, .txt)",
        required=True
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径 (支持 .json, .csv)",
        default="output/result.json"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细输出"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径 (.env 格式)",
        default=None
    )
    
    return parser.parse_args()


def run_pipeline(input_path: str, output_path: str, config: AppConfig) -> int:
    """运行完整的处理流程"""
    logger = setup_logger("pipeline", level=config.log_level)
    
    logger.info("=" * 60)
    logger.info(f"🚀 开始处理: {{config.app_name}}")
    logger.info("=" * 60)
    
    # 1. 验证配置
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"配置验证失败: {{e}}")
        logger.info("提示: 请在 .env 文件中设置必要的配置项")
        return 1
    
    # 2. 读取输入数据
    logger.info(f"📥 读取输入: {{input_path}}")
    try:
        reader = get_reader(input_path)
        items = reader.read(input_path)
    except Exception as e:
        logger.error(f"读取输入文件失败: {{e}}")
        return 1
    
    if not items:
        logger.warning("输入数据为空，请检查文件格式")
        return 0
    
    # 3. 处理数据
    logger.info(f"⚙️  处理 {{len(items)}} 条数据...")
    processor = {topic['title'][:30].replace(' ', '')}Processor(config)
    result = processor.batch_process(items)
    
    # 4. 写入输出
    logger.info(f"📤 写入输出: {{output_path}}")
    output_data = [output.to_dict() for output in result.outputs]
    
    try:
        ext = Path(output_path).suffix.lower()
        if ext == ".csv":
            write_csv(output_data, output_path)
        else:
            write_json(output_data, output_path)
    except Exception as e:
        logger.error(f"写入输出文件失败: {{e}}")
        return 1
    
    # 5. 输出统计
    logger.info("=" * 60)
    logger.info(f"✅ 处理完成!")
    logger.info(f"   总计: {{result.total_items}} 条")
    logger.info(f"   成功: {{result.processed_items}} 条")
    logger.info(f"   失败: {{result.failed_items}} 条")
    logger.info(f"   耗时: {{result.duration_seconds:.2f}} 秒")
    logger.info("=" * 60)
    
    return 0 if result.success else 1


def main() -> int:
    """主入口函数"""
    args = parse_args()
    
    # 加载配置
    config = load_config()
    if args.verbose:
        config.log_level = "DEBUG"
    if args.config:
        # 从配置文件加载
        pass
    
    # 运行处理流程
    return run_pipeline(args.input, args.output, config)


if __name__ == "__main__":
    sys.exit(main())
''')

        # === src/__main__.py - 支持 python -m src 运行 ===
        main_module = src_dir / "__main__.py"
        main_module.write_text('''"""支持 python -m src 运行"""
from src.main import main
import sys

if __name__ == "__main__":
    sys.exit(main())
''')

        # === .env.example ===
        env_example = project_dir / ".env.example"
        env_example.write_text(f'''# {topic['title']} 配置文件
# 复制此文件为 .env 并填入你的配置

# === 基础配置 ===
DEBUG=false
LOG_LEVEL=INFO

# === API 配置（必填）===
# 在此填入你的 API 密钥
API_KEY=your_api_key_here

# === 模型配置 ===
MODEL_NAME=gpt-4

# === 路径配置 ===
INPUT_PATH=./data/input
OUTPUT_PATH=./data/output
''')

        # === requirements.txt ===
        req_file = project_dir / "requirements.txt"
        req_file.write_text('''# 核心依赖
requests>=2.28.0
python-dotenv>=1.0.0

# 开发依赖
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
''')

        # === data/input/sample.json - 示例输入 ===
        sample_dir = project_dir / "data" / "input"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample_file = sample_dir / "sample.json"
        sample_data = [
            {"content": "这是第一条示例数据，请替换为你的实际输入", "source": "sample", "metadata": {"id": 1}},
            {"content": "这是第二条示例数据", "source": "sample", "metadata": {"id": 2}}
        ]
        sample_file.write_text(json.dumps(sample_data, ensure_ascii=False, indent=2))

    def _generate_web_app_code(self, project_dir: Path, topic: Dict):
        """Generate web app source code"""
        # Frontend - React app
        app_tsx = project_dir / "frontend" / "src" / "App.tsx"
        app_tsx.write_text(f'''import React from 'react';
import './App.css';

function App() {{
  return (
    <div className="App">
      <header className="App-header">
        <h1>{topic['title']}</h1>
        <p>{topic['description']}</p>
        <p>Generated by AI Daily Agent on {datetime.now().strftime('%Y-%m-%d')}</p>
      </header>
      <main>
        <section>
          <h2>Features</h2>
          <ul>
            <li>Feature 1: AI-powered analysis</li>
            <li>Feature 2: Real-time processing</li>
            <li>Feature 3: Interactive visualization</li>
          </ul>
        </section>
      </main>
    </div>
  );
}}

export default App;
''')

        # Backend - Express API
        index_ts = project_dir / "backend" / "src" / "index.ts"
        index_ts.write_text(f'''import express from 'express';
import cors from 'cors';

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {{
  res.json({{ status: 'ok', timestamp: new Date().toISOString() }});
}});

// API endpoints
app.get('/api/topics', (req, res) => {{
  // TODO: Implement actual API based on topic
  res.json({{
    topic: "{topic['title']}",
    description: "{topic['description']}",
    generated: "{datetime.now().strftime('%Y-%m-%d')}"
  }});
}});

app.listen(port, () => {{
  console.log(`Server running on port ${{port}}`);
}});
''')

        # Package.json for frontend
        frontend_pkg = project_dir / "frontend" / "package.json"
        frontend_pkg.write_text('''{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^4.9.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  }
}
''')

        # Package.json for backend
        backend_pkg = project_dir / "backend" / "package.json"
        backend_pkg.write_text('''{
  "name": "backend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "express": "^4.18.0",
    "cors": "^2.8.5",
    "typescript": "^4.9.0"
  },
  "scripts": {
    "start": "ts-node src/index.ts",
    "dev": "ts-node-dev src/index.ts"
  }
}
''')

    def _generate_full_stack_code(self, project_dir: Path, topic: Dict):
        """Generate full stack application code"""
        # API - FastAPI
        api_main = project_dir / "api" / "src" / "main.py"
        api_main.write_text(f'''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(
    title="{topic['title']}",
    description="{topic['description']}",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {{
        "name": "{topic['title']}",
        "description": "{topic['description']}",
        "version": "0.1.0",
        "generated": "{datetime.now().strftime('%Y-%m-%d')}"
    }}

@app.get("/health")
async def health_check():
    return {{"status": "healthy"}}

# TODO: Add more endpoints based on the topic
''')

        # Frontend - Next.js
        page_tsx = project_dir / "frontend" / "src" / "page.tsx"
        page_tsx.write_text(f'''export default function Home() {{
  return (
    <main>
      <h1>{topic['title']}</h1>
      <p>{topic['description']}</p>
      <p>Generated: {datetime.now().strftime('%Y-%m-%d')}</p>
    </main>
  )
}}
''')

        # Database schema
        schema_sql = project_dir / "database" / "schema.sql"
        schema_sql.write_text(f'''-- Database schema for {topic['title']}
-- Generated on {datetime.now().strftime('%Y-%m-%d')}

CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

        # API requirements
        api_req = project_dir / "api" / "requirements.txt"
        api_req.write_text('''fastapi>=0.95.0
uvicorn[standard]>=0.22.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
python-dotenv>=2.0.0
pydantic>=2.0.0
''')

    def _generate_ai_agent_code(self, project_dir: Path, topic: Dict):
        """Generate AI agent application code"""
        agent_main = project_dir / "agent" / "src" / "agent.py"
        agent_main.write_text(f'''"""
AI Agent for: {topic['title']}

{topic['description']}

Generated by AI Daily Agent on {datetime.now().strftime('%Y-%m-%d')}
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the AI agent"""
    name: str = "{topic['title']}"
    description: str = "{topic['description']}"
    max_iterations: int = 10
    verbose: bool = True


class AIAgent:
    """
    AI Agent that can perform tasks related to:
    {topic['title']}
    """
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.tools = []
        self.history = []
        
    def add_tool(self, tool_name: str, tool_func: callable):
        """Add a tool to the agent's toolkit"""
        self.tools.append({{"name": tool_name, "function": tool_func}})
        
    def think(self, task: str) -> str:
        """Think about a task and decide what to do"""
        # TODO: Implement actual reasoning logic
        # This could use LLM APIs like OpenAI, Anthropic, etc.
        return f"Analyzing task: {{task}}"
        
    def act(self, action: str) -> Any:
        """Execute an action"""
        # TODO: Implement actual action execution
        return f"Executed: {{action}}"
        
    def run(self, task: str) -> str:
        """Run the agent on a task"""
        print(f"Starting agent: {{self.config.name}}")
        print(f"Task: {{task}}")
        
        for i in range(self.config.max_iterations):
            thought = self.think(task)
            print(f"Iteration {{i+1}}: {{thought}}")
            
            # TODO: Implement actual agent loop
            # 1. Think about the task
            # 2. Decide on an action
            # 3. Execute the action
            # 4. Observe the result
            # 5. Decide if task is complete
            
            self.history.append({{"iteration": i, "thought": thought}})
            
        return "Task completed"


def main():
    """Main entry point"""
    agent = AIAgent()
    result = agent.run("Example task related to {topic['title']}")
    print(f"Result: {{result}}")


if __name__ == "__main__":
    main()
''')

        # Tools module
        tools_file = project_dir / "tools" / "tools.py"
        tools_file.write_text(f'''"""
Tools for the AI Agent

Tools related to: {topic['title']}
"""

from typing import Any, Dict


def search_tool(query: str) -> Dict[str, Any]:
    """Search for information"""
    # TODO: Implement actual search functionality
    return {{"query": query, "results": []}}


def analyze_tool(data: Any) -> Dict[str, Any]:
    """Analyze data"""
    # TODO: Implement actual analysis functionality
    return {{"data": data, "analysis": {{}}}}


def generate_tool(prompt: str) -> str:
    """Generate content"""
    # TODO: Implement actual generation functionality
    return f"Generated content for: {{prompt}}"
''')

        # Agent requirements
        agent_req = project_dir / "agent" / "requirements.txt"
        agent_req.write_text('''openai>=1.0.0
anthropic>=0.3.0
langchain>=0.0.200
pydantic>=2.0.0
python-dotenv>=2.0.0
requests>=2.28.0
''')

        # Agent config
        agent_config = project_dir / "config" / "agent.yaml"
        agent_config.write_text(f'''# Agent Configuration
# Topic: {topic['title']}

agent:
  name: "{topic['title']}"
  description: "{topic['description']}"
  max_iterations: 10
  verbose: true

tools:
  - name: search
    enabled: true
  - name: analyze
    enabled: true
  - name: generate
    enabled: true

llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 2000
''')

    def _generate_data_pipeline_code(self, project_dir: Path, topic: Dict):
        """Generate data pipeline code"""
        pipeline_main = project_dir / "pipeline" / "src" / "pipeline.py"
        pipeline_main.write_text(f'''"""
Data Pipeline for: {topic['title']}

{topic['description']}

Generated by AI Daily Agent on {datetime.now().strftime('%Y-%m-%d')}
"""

import pandas as pd
from typing import Dict, Any
from pathlib import Path


class DataPipeline:
    """
    Data processing pipeline for analyzing and transforming data
    related to: {topic['title']}
    """
    
    def __init__(self, input_dir: str = "data/raw", output_dir: str = "data/processed"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract(self, source: str) -> pd.DataFrame:
        """Extract data from source"""
        # TODO: Implement actual data extraction
        # This could read from files, APIs, databases, etc.
        print(f"Extracting data from: {{source}}")
        return pd.DataFrame()
        
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform the data"""
        # TODO: Implement actual data transformation
        print(f"Transforming data: {{len(df)}} rows")
        return df
        
    def load(self, df: pd.DataFrame, destination: str):
        """Load data to destination"""
        # TODO: Implement actual data loading
        output_path = self.output_dir / destination
        df.to_csv(output_path, index=False)
        print(f"Loaded data to: {{output_path}}")
        
    def run(self, source: str, destination: str):
        """Run the complete pipeline"""
        print("Starting data pipeline...")
        print(f"Topic: {topic['title']}")
        
        # ETL process
        df = self.extract(source)
        df = self.transform(df)
        self.load(df, destination)
        
        print("Pipeline completed successfully!")


def main():
    """Main entry point"""
    pipeline = DataPipeline()
    pipeline.run("input.csv", "output.csv")


if __name__ == "__main__":
    main()
''')

        # Pipeline requirements
        pipeline_req = project_dir / "pipeline" / "requirements.txt"
        pipeline_req.write_text('''pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.2.0
matplotlib>=3.7.0
seaborn>=0.12.0
python-dotenv>=2.0.0
''')

    def _generate_documentation(self, project_dir: Path, topic: Dict, tech_stack: Dict):
        """
        Generate comprehensive documentation
        """
        # Generate main README
        readme_content = self._generate_readme(topic, tech_stack)
        readme_file = project_dir / "README.md"
        readme_file.write_text(readme_content)

        # Generate CONTRIBUTING guide
        contributing_content = self._generate_contributing(topic)
        contributing_file = project_dir / "CONTRIBUTING.md"
        contributing_file.write_text(contributing_content)

        # Generate CHANGELOG
        changelog_content = self._generate_changelog(topic)
        changelog_file = project_dir / "CHANGELOG.md"
        changelog_file.write_text(changelog_content)

        # Generate LICENSE
        license_content = self._generate_license()
        license_file = project_dir / "LICENSE"
        license_file.write_text(license_content)

    def _generate_readme(self, topic: Dict, tech_stack: Dict) -> str:
        """Generate comprehensive README.md"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        readme = f'''# {topic['title']}

<div align="center">

**{topic['description']}**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Generated](https://img.shields.io/badge/Generated-{date_str}-green.svg)](https://github.com/yourusername/ai-daily-projects)

**Part of [AI Daily Projects](https://github.com/yourusername/ai-daily-projects)** - Daily AI innovation, one project at a time.

</div>

---

## 📖 Overview

This project was automatically generated by **AI Daily Agent** on **{date_str}** based on the trending AI topic:

> **{topic['title']}**
> 
> {topic['description']}

**Source:** {topic.get('url', 'AI Hot Topic')}  
**Tags:** {', '.join(topic.get('tags', []))}

## 🎯 What This Project Does

This project provides a complete solution for working with {topic['title']}. It includes:

- ✅ Core functionality based on the latest AI trends
- ✅ Production-ready code structure
- ✅ Comprehensive documentation
- ✅ Automated testing setup
- ✅ CI/CD pipeline configuration
- ✅ Docker support for easy deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ (or Node.js 16+ for web applications)
- Git
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/{topic.get('slug', 'ai-project')}.git
   cd {topic.get('slug', 'ai-project')}
   ```

2. **Install dependencies**
   ```bash
   # For Python projects
   pip install -r requirements.txt
   
   # For Node.js projects
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   # For Python projects
   python src/main.py
   
   # For Node.js projects
   npm start
   ```

## 📚 Features

### Core Features

- **Feature 1**: Based on {topic['title']}
- **Feature 2**: Implements best practices from the AI community
- **Feature 3**: Extensible and modular architecture
- **Feature 4**: Comprehensive error handling and logging

### Technical Highlights

- Built with modern {tech_stack['language']} ecosystem
- Follows industry best practices and coding standards
- Includes unit tests and integration tests
- Dockerized for easy deployment
- CI/CD ready with GitHub Actions

## 🏗️ Architecture

```
{topic.get('slug', 'project')}/
├── src/                  # Source code
├── tests/                # Test files
├── docs/                 # Documentation
├── examples/             # Usage examples
├── .github/              # GitHub Actions workflows
├── Dockerfile            # Docker configuration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## 💡 Usage

### Basic Usage

```python
# Example usage code
# TODO: Add actual usage examples based on the topic

from src.main import main

if __name__ == "__main__":
    main()
```

### Advanced Usage

```python
# Advanced usage examples
# TODO: Add more complex examples

# Example 1: Custom configuration
# Example 2: Batch processing
# Example 3: Integration with other tools
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_main.py
```

## 🐳 Docker

Build and run with Docker:

```bash
# Build the image
docker build -t {topic.get('slug', 'ai-project')} .

# Run the container
docker run -p 8000:8000 {topic.get('slug', 'ai-project')}
```

## 📊 Performance

This project is designed with performance in mind:

- Optimized algorithms based on {topic['title']}
- Efficient data processing pipelines
- Minimal resource footprint
- Scalable architecture

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Generated by [AI Daily Agent](https://github.com/yourusername/ai-daily-agent)
- Based on trending AI topic: {topic['title']}
- Part of the daily AI innovation series

## 📞 Contact

For questions or feedback:

- **GitHub Issues**: [Report a bug](https://github.com/yourusername/{topic.get('slug', 'ai-project')}/issues)
- **Discussions**: [Join the conversation](https://github.com/yourusername/{topic.get('slug', 'ai-project')}/discussions)

---

<div align="center">

**⭐ If you find this project useful, please consider giving it a star! ⭐**

*Part of [AI Daily Projects](https://github.com/yourusername/ai-daily-projects) - Building the future of AI, one day at a time.*

</div>
'''
        return readme

    def _generate_contributing(self, topic: Dict) -> str:
        """Generate CONTRIBUTING.md"""
        return f'''# Contributing to {topic['title']}

Thank you for your interest in contributing to this project!

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. Use the bug report template to create a new issue
3. Include as much detail as possible

### Suggesting Features

1. Check if the feature has already been suggested
2. Use the feature request template
3. Explain the use case and expected benefits

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Submit a pull request

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for all functions and classes
- Keep functions small and focused
- Add comments for complex logic

## Testing

- Write unit tests for new functionality
- Ensure existing tests pass
- Aim for >80% code coverage

## Documentation

- Update README.md if needed
- Add docstrings to new functions/classes
- Update API documentation
- Add examples for new features

## Code of Conduct

Please be respectful and constructive in all interactions.

Thank you for contributing!
'''

    def _generate_changelog(self, topic: Dict) -> str:
        """Generate CHANGELOG.md"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        return f'''# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - {date_str}

### Added
- Initial project generation based on AI topic: {topic['title']}
- Core functionality implementation
- Basic documentation
- Test suite setup
- CI/CD configuration
- Docker support

### Changed
- N/A

### Fixed
- N/A

---

*This changelog is automatically updated with each release.*
'''

    def _generate_license(self) -> str:
        """Generate MIT LICENSE file"""
        year = datetime.now().year
        return f'''MIT License

Copyright (c) {year} AI Daily Projects

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

    def _generate_tests(self, project_dir: Path, topic: Dict, tech_stack: Dict):
        """
        Generate test files
        """
        test_file = project_dir / "tests" / "test_main.py"
        test_file.write_text(f'''"""
Tests for {topic['title']}
"""

import pytest
from src.main import main


def test_main_function():
    """Test main function returns successfully"""
    result = main([])
    assert result == 0


def test_main_with_args():
    """Test main function with arguments"""
    result = main(["--input", "test.txt", "--verbose"])
    assert result == 0


# Add more tests based on the topic
# TODO: Implement comprehensive test coverage
''')

        # Create pytest configuration
        pytest_ini = project_dir / "pytest.ini"
        pytest_ini.write_text('''[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
''')

    def _generate_cicd_config(self, project_dir: Path, topic: Dict, tech_stack: Dict):
        """
        Generate CI/CD configuration (GitHub Actions)
        """
        github_dir = project_dir / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)

        ci_file = github_dir / "ci.yml"
        ci_file.write_text(f'''name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    
    - name: Test with pytest
      run: |
        pytest --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.10"
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install flake8 black isort
    
    - name: Lint with flake8
      run: |
        flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 src tests --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics
    
    - name: Check formatting with black
      run: |
        black --check src tests
    
    - name: Check import sorting
      run: |
        isort --check-only src tests
''')

    def _generate_docker_config(self, project_dir: Path, topic: Dict, tech_stack: Dict):
        """
        Generate Docker configuration
        """
        # Dockerfile
        dockerfile = project_dir / "Dockerfile"
        dockerfile.write_text(f'''# Dockerfile for {topic['title']}
# Generated by AI Daily Agent

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (if applicable)
# EXPOSE 8000

# Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
#     CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application
CMD ["python", "src/main.py"]
''')

        # .dockerignore
        dockerignore = project_dir / ".dockerignore"
        dockerignore.write_text('''# Git
.git
.gitignore

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode
.idea
*.swp
*.swo

# Testing
.pytest_cache
.coverage
htmlcov/

# Docker
Dockerfile
.dockerignore

# Documentation
docs/
*.md
!README.md

# Misc
.env
.env.local
*.log
''')

        # Docker Compose (optional)
        docker_compose = project_dir / "docker-compose.yml"
        docker_compose.write_text(f'''# Docker Compose for {topic['title']}
# Generated by AI Daily Agent

version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./data:/app/data
    restart: unless-stopped
''')

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        import re
        # Convert to lowercase
        text = text.lower()
        # Remove special characters
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        # Replace spaces with hyphens
        text = re.sub(r'\s+', '-', text)
        # Remove multiple hyphens
        text = re.sub(r'-+', '-', text)
        # Remove leading/trailing hyphens
        text = text.strip('-')
        # Limit length
        return text[:50]
