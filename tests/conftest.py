"""pytest 配置：将项目根目录加入 sys.path，使测试可直接导入 config/core/utils。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
