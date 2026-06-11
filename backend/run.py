# -*- coding: utf-8 -*-
"""
织梦绮谭 - 启动脚本

在 PyCharm 中配置此文件为 Run Configuration 即可一键启动。
也可以命令行运行:
    cd backend
    python run.py
"""

import sys
import io
import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    # 修复 Windows 控制台 GBK 编码问题，确保中文和特殊字符正常输出
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass  # 如果 buffer 已关闭则跳过（如 uvicorn reload 子进程）

    settings = get_settings()
    print("=" * 50)
    print("  织梦绮谭")
    print("=" * 50)
    print(f"  地址: http://{settings.app_host}:{settings.app_port}")
    print(f"  文档: http://{settings.app_host}:{settings.app_port}/docs")
    print(f"  模型: {settings.deepseek_model}")
    print("=" * 50)
    print()

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
