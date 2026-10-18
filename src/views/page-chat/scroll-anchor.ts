/**
 * 「向上加载更早内容」时的滚动锚定。
 *
 * 场景：AI 对话 / 聊天室下拉刷新时，从接口取回更早的一页消息并插到列表**顶部**。
 *
 * 问题：内容变高时浏览器会把 `scrollTop` 的**数值**保持不变，于是视口里看到的
 * 内容整体上移——用户下拉一次，看到的是刚加载出来的那几条最旧消息，原本正在读
 * 的内容被顶出了屏幕，观感就是「拉一下、跳一下」。
 *
 * 想要的效果：视口内容原地不动，只在上面多出几条。
 *
 * 做法：插入前后各读一次滚动容器的 `scrollHeight`，把差值补到 `scrollTop` 上。
 *
 * 与 Ionic 下拉刷新配合是自洽的：`ion-refresher` 是 `slot="fixed"`，靠
 * `transform: translateY()` 把内容往下推（源码见
 * `@ionic/core` 的 `refresher.setCss()`），不改变 `scrollHeight`；补完 `scrollTop`
 * 之后刷新条收起、transform 归零，视口正好回到下拉之前的位置。
 *
 * 注意：本方案依赖插入内容的高度在**测量时**就已确定。列表里的图片都写死了
 * 尺寸（`w-28 h-28`），不会在图片加载完成后再撑高，因此不需要额外的二次校正。
 */

/** 插入内容之前的滚动状态快照。 */
export interface ScrollAnchor {
  /** 插入前的可滚动总高度 */
  scrollHeight: number;
}

/** 只依赖这两个属性的最小结构，便于测试里传假对象。 */
export interface ScrollElementLike {
  scrollTop: number;
  scrollHeight: number;
}

/** Ionic `ion-content` 实例上与滚动相关的最小结构。 */
interface IonicContentLike {
  $el?: {
    getScrollElement?: () => Promise<ScrollElementLike | null | undefined>;
  };
}

/**
 * 记录插入前的高度。返回 `null` 表示无法测量（元素不可用 / 数值异常），
 * 调用方应跳过后续的恢复动作。
 */
export function captureScrollAnchor(
  el: ScrollElementLike | null | undefined
): ScrollAnchor | null {
  if (!el) return null;
  const scrollHeight = Number(el?.scrollHeight);
  if (!Number.isFinite(scrollHeight)) return null;
  return { scrollHeight };
}

/**
 * 按插入前后高度差补偿 `scrollTop`，使视口内容保持原位。
 *
 * 必须在 DOM 更新完成之后调用（组件里先 `await nextTick()`）。
 *
 * @returns 实际补偿的像素数（0 表示没有变化）。
 */
export function restoreScrollAnchor(
  el: ScrollElementLike | null | undefined,
  anchor: ScrollAnchor | null
): number {
  if (!el || !anchor) return 0;

  const current = Number(el?.scrollHeight);
  if (!Number.isFinite(current)) return 0;

  const delta = current - anchor.scrollHeight;
  // 高度没变（没有新内容 / 内容被去重掉了）就不动，避免误滚
  if (!Number.isFinite(delta) || delta === 0) return 0;

  const before = Number(el.scrollTop) || 0;
  // 不允许滚到负值：列表在空/极短时会出现负 delta
  el.scrollTop = Math.max(0, before + delta);
  return el.scrollTop - before;
}

/**
 * 取 `ion-content` 内部的滚动元素。
 *
 * 拿不到时返回 `null`，让调用方退化成「不做锚定」而不是抛错——
 * 锚定只是体验优化，不能因为它导致刷新失败。
 */
export async function getContentScrollElement(
  content: unknown
): Promise<ScrollElementLike | null> {
  const host = (content as IonicContentLike | null | undefined)?.$el;
  const getter = host?.getScrollElement;
  if (typeof getter !== 'function') return null;
  try {
    return (await getter.call(host)) ?? null;
  } catch {
    return null;
  }
}
