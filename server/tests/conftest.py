"""tests 全局配置：把测试副产物挡在仓库之外。

`core.db.rds_mgr` 在**模块导入时**就确定本地回退文件路径
（`_init_storage()` -> `_local_file_path()` 读环境变量 `RDS_LOCAL_FILE`）。
Redis 不可用时（本机/CI 常见），所有读写都会落到那个文件上。

若不重定向，测试会直接改写仓库根目录下的 `rds_local.json`——它是受 git 跟踪的
文件，于是「跑一次测试」就会让工作区变脏，容易被误提交。

因此这里在任何 core 模块被导入之前把路径指到临时目录。pytest 会先导入
`tests/conftest.py` 再导入各级子目录的 conftest 与测试模块，所以这个时机是安全的。
"""

import atexit
import os
import shutil
import tempfile

_rds_tmp_dir = tempfile.mkdtemp(prefix="mytodo_test_rds_")
# setdefault：显式设置过 RDS_LOCAL_FILE 的环境保持优先
os.environ.setdefault("RDS_LOCAL_FILE", os.path.join(_rds_tmp_dir, "rds_local.json"))
atexit.register(shutil.rmtree, _rds_tmp_dir, ignore_errors=True)
