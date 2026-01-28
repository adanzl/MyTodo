from dashscope import Generation
import time

from core.ai.base_ali import BaseAli, log, ALI_KEY

MODEL = "qwen-plus"



class TxtAli(BaseAli):
    """
    Txt Ali API
    """

    def __init__(self):
        super().__init__("Txt")

    def query(self, txt: str, prompt: str = "") -> tuple[str, str]:
        """查询 Txt Ali API
        
        Args:
            txt: 文本内容
            prompt: 可选的自定义提示（留空时使用内置 PROMPT）
        
        Returns:
            tuple: (状态, 提取的文章内容)
                - 状态: "ok" 表示成功, "error" 表示失败
                - 内容: 成功时返回提取的文本，失败时返回 None
        """

        start_time = time.time()

        try:
            # 统一转换为列表处理
            log.info(f"[Txt] 开始处理 Txt 请求，文本长度: {len(txt)}")

            # 构建消息内容：提示 + 待分析的文章
            content = [{"text": f"{prompt}\n\n---文章内容---\n{txt}"}]

            messages = [{
                "role": "system",
                "content": "你是一名文字处理助手，请根据用户提供的文章，生成一篇和指定参考格式完全一致的文本分析结构化文档",
            }, {
                "role": "user",
                "content": content,
            }]

            response = Generation.call(
                api_key=ALI_KEY,
                model=MODEL,
                messages=messages,
                result_format="message",
            )
            # 检查响应是否有效
            ret, content = self.validate_response(response)
            if ret != "ok":
                return ret, content

            # 从 content 中提取文本（可能是 list[{"text": "..."}] 或 str）
            result_text = content
            if not result_text:
                log.warning("[Txt] API 返回内容为空")
                return "error", "API 响应格式错误：返回内容为空"

            # 记录成功信息
            total_elapsed = time.time() - start_time
            log.info(f"[Txt] 文本分析成功，结果长度: {len(result_text)} 字符，总耗时: {total_elapsed:.2f}秒")

            return "ok", result_text
        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            log.error(f"[Txt] 文本分析失败，耗时: {elapsed:.2f}秒，错误: {e}", exc_info=True)
            return "error", None


if __name__ == "__main__":
    txt_ali = TxtAli()
    # 测试单张图片
    article = """杯弓蛇影

古时候，有个叫乐广的人，他非常热情好客，朋友也很多。他常常邀请一大帮朋友聚在一起喝酒、吟诗、赏乐。有一天，乐广突然发现，有个和自己很亲密的好朋友已经有好多天都没有来参加聚会了。他觉得很疑惑，心里一直记着这件事，想着下次见面一定要当面问问缘由。

又过了好久，这个朋友来聚会了，乐广就问起了缘由。好友笑笑，回答道：“让您见笑了。上次我们一起聚会，承蒙赐给我的酒，我刚要喝，忽然发现酒杯中有一条弯弯曲曲的蛇，杯动蛇也动。我心里特别厌恶它，但酒又不能不喝，结果喝了酒就害起病来，到现在心中还有恐惧呢。”

乐广听了，也感到非常奇怪，有蛇？那是根本不可能的啊！到底是怎么回事呢？他细细地回想着上次的聚会。

他在大厅里踱着方步思考着，突然看到了大厅墙上挂着一张弓，弓的影子正好映在水里。他想到了，朋友所说的蛇一定就是这张弓的影子了。想到这，他不由得笑出了声。“原来如此啊！”

又要开席了，乐广特意又安排好友坐到了上次那个位置，还在他面前倒满一杯酒，然后问道：“在酒中看到什么了没有？”那好友定睛一看，酒杯中还是浮着一条弯弯曲曲的蛇，和上次的一模一样。他脸色大变，吓得站起来，倒退了好几步。

乐广哈哈大笑，对他说：“其实你不用害怕，那只不过墙上的那张弓的影子而已！”那朋友恍然大悟，积久难治的疾病也好了。

《杯弓蛇影》中，朋友将映在酒杯里的弓影误认为蛇，导致内心恐惧。这启示我们在面对问题时，不要疑神疑鬼，被表象所迷惑，从而产生不必要的恐慌。遇到难题，应冷静思考，深入探究真相，以科学理性的态度去分析和判断，避免因错误的判断而给自己带来困扰，影响对问题的正确处理。"""
    _, result = txt_ali.query(txt=article)
    print(result)
