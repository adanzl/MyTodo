import { describe, expect, it, vi } from 'vitest';
import {
  captureScrollAnchor,
  getContentScrollElement,
  restoreScrollAnchor,
} from '@/views/page-chat/scroll-anchor';

/** 只会被读写的两个字段，正好覆盖锚定逻辑用到的全部。 */
function fakeScrollEl(scrollTop = 0, scrollHeight = 500) {
  return { scrollTop, scrollHeight };
}

describe('captureScrollAnchor', () => {
  it('records the scroll height so the delta can be measured later', () => {
    expect(captureScrollAnchor(fakeScrollEl(0, 800))).toEqual({ scrollHeight: 800 });
  });

  it('returns null when there is no scroll element', () => {
    expect(captureScrollAnchor(null)).toBeNull();
    expect(captureScrollAnchor(undefined)).toBeNull();
  });

  it('returns null when the height is not a number', () => {
    expect(captureScrollAnchor({ scrollTop: 0, scrollHeight: Number.NaN })).toBeNull();
  });
});

describe('restoreScrollAnchor', () => {
  it('keeps the viewport still when content is prepended', () => {
    // 下拉刷新前：视口在顶部，内容高 500
    const el = fakeScrollEl(0, 500);
    const anchor = captureScrollAnchor(el);

    // 上面插入了 300px 的更早消息
    el.scrollHeight = 800;

    expect(restoreScrollAnchor(el, anchor)).toBe(300);
    expect(el.scrollTop).toBe(300);
  });

  it('also compensates when the user was not at the very top', () => {
    const el = fakeScrollEl(120, 900);
    const anchor = captureScrollAnchor(el);

    el.scrollHeight = 1100;

    expect(restoreScrollAnchor(el, anchor)).toBe(200);
    expect(el.scrollTop).toBe(320);
  });

  it('does nothing when no content was added', () => {
    // 例如接口返回的消息全被去重掉：高度没变，绝不能滚动
    const el = fakeScrollEl(0, 500);
    const anchor = captureScrollAnchor(el);

    expect(restoreScrollAnchor(el, anchor)).toBe(0);
    expect(el.scrollTop).toBe(0);
  });

  it('never scrolls above the top', () => {
    // 高度变小（例如错误提示条消失）时不应产生负的 scrollTop
    const el = fakeScrollEl(40, 500);
    const anchor = captureScrollAnchor(el);

    el.scrollHeight = 300;

    expect(restoreScrollAnchor(el, anchor)).toBe(-40);
    expect(el.scrollTop).toBe(0);
  });

  it('is a no-op without an anchor', () => {
    const el = fakeScrollEl(0, 500);
    expect(restoreScrollAnchor(el, null)).toBe(0);
    expect(el.scrollTop).toBe(0);
  });

  it('is a no-op without a scroll element', () => {
    expect(restoreScrollAnchor(null, { scrollHeight: 0 })).toBe(0);
  });

  it('survives a bogus scrollTop value', () => {
    const el = { scrollTop: Number.NaN, scrollHeight: 500 };
    const anchor = captureScrollAnchor(el);
    el.scrollHeight = 700;

    expect(restoreScrollAnchor(el, anchor)).toBe(200);
    expect(el.scrollTop).toBe(200);
  });
});

describe('getContentScrollElement', () => {
  it('reads the element from an ion-content instance', async () => {
    const scrollEl = fakeScrollEl();
    const content = { $el: { getScrollElement: vi.fn(async () => scrollEl) } };

    expect(await getContentScrollElement(content)).toBe(scrollEl);
    expect(content.$el.getScrollElement).toHaveBeenCalledOnce();
  });

  it('returns null when the content has no scroll accessor', async () => {
    expect(await getContentScrollElement(null)).toBeNull();
    expect(await getContentScrollElement({})).toBeNull();
    expect(await getContentScrollElement({ $el: {} })).toBeNull();
  });

  it('returns null when the element is not ready yet', async () => {
    const content = {
      $el: { getScrollElement: async (): Promise<undefined> => undefined },
    };
    expect(await getContentScrollElement(content)).toBeNull();
  });

  it('swallows failures so a refresh is never broken by anchoring', async () => {
    const content = {
      $el: {
        getScrollElement: async () => {
          throw new Error('content not ready');
        },
      },
    };
    expect(await getContentScrollElement(content)).toBeNull();
  });
});
