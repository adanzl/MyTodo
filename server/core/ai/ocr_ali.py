from dashscope import MultiModalConversation
import dashscope

try:
    from core.config import app_logger, config

    log = app_logger
    ALI_KEY = config.ALI_KEY
except ImportError:
    from dotenv import load_dotenv
    import os

    load_dotenv()
    import logging

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    log = logging.getLogger()
    ALI_KEY = os.getenv('ALI_KEY', '')
    print(f"use default log and ALI_KEY: {ALI_KEY}")

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
local_file = r"C:\Users\adanz\Downloads\楚人学舟.jpg"
PROMPT = """请从图片中提取文章内容，要求如下：

## 提取要求
1. **内容提取**：准确识别并提取图片中的所有文字内容
2. **多图处理**：如果有多张图片，请按照图片内容的逻辑顺序（从左到右、从上到下）进行排列和合并
3. **内容过滤**：过滤掉以下非文章故事内容：
   - 批注、注释、标记
   - 页码、页眉、页脚
   - 水印、印章
   - 图片说明、图注
4. **内容排除**：以下相关的段落删除：
   - 寓意点播

## 准确性要求
- 必须准确无误地提取文字，不得遗漏关键信息
- 严禁编造或添加图片中不存在的文字
- 对于因模糊、强光遮挡等原因无法识别的单个字符，使用英文问号"?"代替
- 保持原文的段落结构和换行

## 输出格式
- 返回纯文本格式
- 不要包含任何格式标记（如 Markdown、HTML 等）
- 保持原文的自然段落分隔"""


class OCRAli:
    """
    OCR Ali API
    """

    def __init__(self):
        pass

    def query(self, image_paths: str | list[str]) -> tuple[str, str]:
        """查询 OCR Ali API
        
        Args:
            image_paths: 图片路径，可以是单个路径字符串或路径列表
        
        Returns:
            tuple: (状态, 提取的文章内容)
                - 状态: "ok" 表示成功, "error" 表示失败
                - 内容: 成功时返回提取的文本，失败时返回 None
        """
        try:
            # 统一转换为列表处理
            if isinstance(image_paths, str):
                image_paths = [image_paths]

            if not image_paths:
                log.error("OCR Ali API error: 图片路径列表为空")
                return "error", "图片路径列表为空"

            # 构建消息内容：先添加所有图片，最后添加文本提示
            content = []
            for image_path in image_paths:
                content.append({
                    "image": image_path,
                    "min_pixels": 32 * 32 * 3,
                    "max_pixels": 32 * 32 * 8192,
                    "enable_rotate": False,
                })

            # 添加文本提示
            content.append({
                "text": PROMPT
            })

            messages = [{
                "role": "user",
                "content": content,
            }]

            response = MultiModalConversation.call(
                api_key=ALI_KEY,
                model="qwen-vl-ocr-latest",
                messages=messages,
            )
            txt = response["output"]["choices"][0]["message"].content[0][
                "text"]
            return "ok", txt
        except Exception as e:
            log.error(f"OCR Ali API error: {e}")
            return "error", None


if __name__ == "__main__":
    ocr_ali = OCRAli()
    # 测试单张图片
    print("单张图片测试:")
    print(ocr_ali.query(image_paths=local_file))
    # 测试多张图片
    # print("多张图片测试:")
    # print(ocr_ali.query(image_paths=[local_file, "path/to/another/image.jpg"]))
