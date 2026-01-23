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

PROMPT = """请从图片中提取文章内容，要求如下：

## 提取要求
1. **内容提取**：准确识别并提取图片中的所有文字内容
2. **多图处理**：如果有多张图片，请按照图片内容的逻辑顺序（从左到右、从上到下）进行排列和合并
3. **内容过滤**：过滤掉以下非文章故事内容：
   - **批注、注释、标记**（必须完全排除，这是最重要的要求）：
     * 文章旁边或周围的批注文字
     * 字体明显小于正文的文字
     * 颜色不是黑色（如灰色、浅色等）的文字
     * 对文章内容进行解释、说明、总结的旁注
     * 任何视觉上明显区别于正文的注释性文字
     * 故事正文结束后出现的任何总结性、解释性、说明性文字
     * 以"为了让"、"虽然...但是"、"虽然...却"等开头，对故事内容进行总结或解释的句子
     * 任何对故事内容进行概括、点评、总结的独立段落或句子
   - 页码、页眉、页脚
   - 水印、印章
   - 图片说明、图注
4. **内容排除**：必须完全删除以下内容，包括标题和后续所有段落：
   - "寓意点拨"及其后续所有内容
   - "寓意点播"及其后续所有内容
   - 在提取到故事正文结束后，如果遇到"寓意点拨"、"寓意点播"等类似标题，立即停止提取，不再返回后续任何内容
   - 故事正文结束后的任何总结性、解释性、说明性文字

## 准确性要求
- 必须准确无误地提取文字，不得遗漏关键信息
- 严禁编造或添加图片中不存在的文字
- 对于因模糊、强光遮挡等原因无法识别的单个字符，使用英文问号"?"代替
- 保持原文的段落结构和换行
- **严格过滤批注**：通过字体大小、颜色等视觉特征识别并完全排除所有批注、注释、旁注内容，只提取正文故事内容
- **故事正文结束判断**：当故事正文内容完整结束后（通常以句号、感叹号、问号结尾），如果后续出现任何对故事进行总结、解释、说明的文字，必须立即停止提取，不返回这些内容
- 故事正文结束后，一旦遇到"寓意点拨"、"寓意点播"等标题，立即停止，不返回该标题及其后续任何内容
- **特别注意**：如果遇到以"为了让"、"虽然...但是"、"虽然...却"、"虽然...但是"等开头，对前面故事内容进行总结或解释的句子，这些是批注，必须完全排除

## 输出格式
- 返回纯文本格式
- 不要包含任何格式标记（如 Markdown、HTML 等）
- 保持原文的自然段落分隔
- 只返回故事正文内容，不包含任何寓意、点评、总结、批注等后续内容
- 故事正文结束后立即停止，不返回任何后续的总结性、解释性文字"""


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
                    # "min_pixels": 3135,
                    "max_pixels": 32 * 32 * 8192,
                    "enable_rotate": True,
                })

            # 添加文本提示
            content.append({"text": PROMPT})

            messages = [{
                "role": "user",
                "content": content,
            }]

            response = MultiModalConversation.call(
                api_key=ALI_KEY,
                model="qwen-vl-ocr-latest",
                messages=messages,
            )

            # 检查响应是否有效
            if not response:
                log.error("OCR Ali API error: 响应为空")
                return "error", "API 响应为空"

            if "output" not in response or not response["output"]:
                log.error(f"OCR Ali API error: 响应中缺少 output 字段，响应: {response}")
                return "error", "API 响应格式错误：缺少 output 字段"

            if "choices" not in response[
                    "output"] or not response["output"]["choices"]:
                log.error(
                    f"OCR Ali API error: 响应中缺少 choices 字段，响应: {response}")
                return "error", "API 响应格式错误：缺少 choices 字段"

            if len(response["output"]["choices"]) == 0:
                log.error("OCR Ali API error: choices 列表为空")
                return "error", "API 响应格式错误：choices 列表为空"

            choice = response["output"]["choices"][0]
            if "message" not in choice or not choice["message"]:
                log.error(
                    f"OCR Ali API error: 响应中缺少 message 字段，choice: {choice}")
                return "error", "API 响应格式错误：缺少 message 字段"

            message = choice["message"]

            # message.content 可能是属性或字典键，需要兼容处理
            content = None
            if hasattr(message, "content"):
                content = message.content
            elif isinstance(message, dict) and "content" in message:
                content = message["content"]
            else:
                log.error(
                    f"OCR Ali API error: 响应中缺少 content 字段，message: {message}")
                return "error", "API 响应格式错误：缺少 content 字段"

            if not content:
                log.error("OCR Ali API error: content 为空")
                return "error", "API 响应格式错误：content 为空"

            # content 可能是列表
            if isinstance(content, list):
                if len(content) == 0:
                    log.error("OCR Ali API error: content 列表为空")
                    return "error", "API 响应格式错误：content 列表为空"
                content_item = content[0]
            else:
                content_item = content

            # 提取文本
            if isinstance(content_item, dict) and "text" in content_item:
                txt = content_item["text"]
            elif hasattr(content_item, "text"):
                txt = content_item.text
            elif isinstance(content_item, str):
                txt = content_item
            else:
                log.error(
                    f"OCR Ali API error: 无法提取 text 字段，content_item: {content_item}"
                )
                return "error", "API 响应格式错误：无法提取 text 字段"

            if not txt:
                log.error("OCR Ali API error: 提取的文本为空")
                return "error", "API 响应格式错误：提取的文本为空"

            return "ok", txt
        except Exception as e:
            log.error(f"OCR Ali API error: {e}")
            return "error", None


if __name__ == "__main__":
    ocr_ali = OCRAli()
    # 测试单张图片
    print("多张图片测试:")
    local_file = [
        r"C:\Users\adanz\Downloads\1.jpg", r"C:\Users\adanz\Downloads\2.jpg"
    ]
    print(ocr_ali.query(image_paths=local_file))
    # 测试多张图片
    # print("多张图片测试:")
    # print(ocr_ali.query(image_paths=[local_file, "path/to/another/image.jpg"]))
