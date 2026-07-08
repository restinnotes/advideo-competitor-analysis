"""文件名安全处理工具"""

import re
import unicodedata


def safe_filename(s: str, max_length: int = 80) -> str:
    """将字符串转换为安全的文件名。

    - 替换 Windows 不允许的字符
    - 归一化 Unicode
    - 截断到 max_length
    """
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r'[\\/:*?"<>|\r\n]', "_", s)
    s = re.sub(r"_+", "_", s).strip("_ .")
    if len(s) > max_length:
        s = s[:max_length].rstrip("_ .")
    return s or "unnamed"
