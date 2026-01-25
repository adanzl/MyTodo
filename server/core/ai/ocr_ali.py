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
2. **标题保留**：**必须完整保留文章的标题**，标题通常位于文章开头，字体较大或加粗，是文章的重要组成部分
3. **多图处理**：如果有多张图片，请按照图片内容的逻辑顺序（从左到右、从上到下）进行排列和合并
4. **必须保留的内容**：
   - **文章标题**：必须完整保留
   - **寓意点拨段落**：必须完整保留"寓意点拨"后面的段落内容，但**不要输出"寓意点拨"这几个字本身**，只保留其后的段落内容。这是文章的重要组成部分，即使字体较小或颜色较浅也要保留
   - **正文内容**：完整提取所有正文故事内容
5. **内容过滤**：过滤掉以下非文章故事内容：
   - **批注、注释、标记**（必须完全排除，但"寓意点拨"段落除外）：
     * 文章旁边或周围的批注文字（不包括"寓意点拨"段落）
     * 字体明显小于正文的文字（但"寓意点拨"段落必须保留）
     * 颜色不是黑色（如灰色、浅色等）的文字（但"寓意点拨"段落即使颜色较浅也必须保留）
     * 任何视觉上明显区别于正文的注释性文字（但"寓意点拨"段落必须保留）
   - **"寓意点拨"标题**：如果图片中有"寓意点拨"这几个字作为标题或标签，**不要输出这几个字**，只输出其后的段落内容
   - 页码、页眉、页脚
   - 水印、印章
   - 图片说明、图注

## 准确性要求
- 必须准确无误地提取文字，不得遗漏关键信息
- **必须完整保留文章标题**：标题是文章的重要组成部分，应完整提取并保留在输出内容的最前面
- **必须完整保留"寓意点拨"段落内容**：无论字体大小、颜色深浅，只要图片中有"寓意点拨"相关的段落内容，都必须完整提取并保留，但**不要输出"寓意点拨"这几个字本身**，只保留其后的段落内容
- 严禁编造或添加图片中不存在的文字
- 对于因模糊、强光遮挡等原因无法识别的单个字符，使用英文问号"?"代替
- 保持原文的段落结构和换行，包括标题与正文之间的段落分隔
- **严格过滤批注**：通过字体大小、颜色等视觉特征识别并完全排除所有批注、注释、旁注内容，但**必须保留"寓意点拨"段落内容**（不包含"寓意点拨"这几个字本身），只提取正文故事内容（但必须保留文章标题和"寓意点拨"段落内容）

## 输出格式
- 返回纯文本格式
- 不要包含任何格式标记（如 Markdown、HTML 等）
- **首先输出文章标题**，然后空一行，再输出正文内容
- 如果图片中有"寓意点拨"相关的段落内容，必须在正文后保留，但**不要输出"寓意点拨"这几个字本身**，只输出其后的段落内容，保持原文的自然段落分隔
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
        import time
        start_time = time.time()

        try:
            # 统一转换为列表处理
            if isinstance(image_paths, str):
                image_paths = [image_paths]

            if not image_paths:
                log.error("[OCR] 图片路径列表为空")
                return "error", "图片路径列表为空"

            log.info(
                f"[OCR] 开始处理 OCR 请求，图片数量: {len(image_paths)}, 图片路径: {image_paths}"
            )

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

            api_start_time = time.time()
            response = MultiModalConversation.call(
                api_key=ALI_KEY,
                model="qwen-vl-plus",
                messages=messages,
            )
            api_elapsed = time.time() - api_start_time
            log.info(f"[OCR] API 调用完成，耗时: {api_elapsed:.2f}秒")

            # 检查响应是否有效
            if not response:
                log.error("[OCR] API 响应为空")
                return "error", "API 响应为空"

            if "output" not in response or not response["output"]:
                log.error(f"[OCR] API 响应中缺少 output 字段，响应: {response}")
                return "error", "API 响应格式错误：缺少 output 字段"

            if "choices" not in response[
                    "output"] or not response["output"]["choices"]:
                log.error(f"[OCR] API 响应中缺少 choices 字段，响应: {response}")
                return "error", "API 响应格式错误：缺少 choices 字段"

            if len(response["output"]["choices"]) == 0:
                log.error("[OCR] API 响应中 choices 列表为空")
                return "error", "API 响应格式错误：choices 列表为空"

            choice = response["output"]["choices"][0]
            if "message" not in choice or not choice["message"]:
                log.error(f"[OCR] API 响应中缺少 message 字段，choice: {choice}")
                return "error", "API 响应格式错误：缺少 message 字段"

            message = choice["message"]

            # message.content 可能是属性或字典键，需要兼容处理
            content = None
            if hasattr(message, "content"):
                content = message.content
            elif isinstance(message, dict) and "content" in message:
                content = message["content"]
            else:
                log.error(f"[OCR] API 响应中缺少 content 字段，message: {message}")
                return "error", "API 响应格式错误：缺少 content 字段"

            if not content:
                log.error("[OCR] API 响应中 content 为空")
                return "error", "API 响应格式错误：content 为空"

            # content 可能是列表
            if isinstance(content, list):
                if len(content) == 0:
                    log.error("[OCR] API 响应中 content 列表为空")
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
                    f"[OCR] 无法提取 text 字段，content_item 类型: {type(content_item)}"
                )
                return "error", "API 响应格式错误：无法提取 text 字段"

            if not txt:
                log.warning("[OCR] 提取的文本为空")
                return "error", "API 响应格式错误：提取的文本为空"

            # 记录成功信息
            text_length = len(txt)
            total_elapsed = time.time() - start_time
            log.info(
                f"[OCR] OCR 处理成功，提取文本长度: {text_length} 字符，总耗时: {total_elapsed:.2f}秒"
            )

            return "ok", txt
        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals(
            ) else 0
            log.error(f"[OCR] OCR 处理失败，耗时: {elapsed:.2f}秒，错误: {e}",
                      exc_info=True)
            return "error", None


if __name__ == "__main__":
    ocr_ali = OCRAli()
    # 测试单张图片
    print("多张图片测试:")
    local_file = [
        r"C:\Users\adanz\Downloads\pic\45-1.jpg",
        r"C:\Users\adanz\Downloads\pic\45-2.jpg",
        r"C:\Users\adanz\Downloads\pic\45-3.jpg",
    ]
    print(ocr_ali.query(image_paths=local_file))
