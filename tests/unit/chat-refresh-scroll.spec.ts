import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, onMounted, ref } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';

const api = vi.hoisted(() => ({
  getChatMessages: vi.fn(),
  getAiChatMessages: vi.fn(),
}));
vi.mock('@/api/api-chat', () => api);
vi.mock('@/api/api-pic', () => ({ getPicDisplayUrl: (name: string) => `/pic/${name}` }));

import TabAiChat from '@/views/page-chat/TabAiChat.vue';
import TabChatRoom from '@/views/page-chat/TabChatRoom.vue';

/**
 * 替代 `ion-content`：把 `getScrollElement` 挂到真实根节点上。
 *
 * 组件是通过 `contentRef.value.$el.getScrollElement()` 取滚动容器的，所以假元素
 * 必须挂在**根 DOM 节点**上，而不是组件实例上。
 */
function contentStub(scrollEl: ScrollFake) {
  return defineComponent({
    name: 'IonContentStub',
    setup(_props, { slots }) {
      const el = ref<HTMLElement | null>(null);
      onMounted(() => {
        if (el.value) {
          (el.value as unknown as { getScrollElement: () => Promise<ScrollFake> }).getScrollElement =
            async () => scrollEl;
        }
      });
      return () => h('div', { ref: el }, slots.default?.());
    },
  });
}

interface ScrollFake {
  scrollTop: number;
  scrollHeight: number;
}

/** jsdom 不做布局，插入内容不会自己变高，这里由接口 mock 显式模拟增长。 */
function growBy(scrollEl: ScrollFake, px: number) {
  scrollEl.scrollHeight += px;
}

/**
 * `shallowMount` 默认把子组件桩掉，而默认桩**不渲染 slot** —— 外层
 * `ion-segment-content` 一旦被桩掉，里面的 `ion-content` 就不会挂载，
 * `contentRef` 永远是 null。所以这里打开 `renderStubDefaultSlot`，
 * 并让 `ion-segment-content` 透传 slot。
 */
const mountOptions = (stub: unknown) => ({
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      IonContent: stub,
      IonSegmentContent: { template: '<div><slot /></div>' },
    },
  },
});

function mountRoom(scrollEl: ScrollFake) {
  const stub = contentStub(scrollEl);
  return shallowMount(TabChatRoom, {
    props: { chatRoomId: 'room-1', userId: 1, getUserInfo: () => undefined },
    ...mountOptions(stub),
  });
}

function mountAiChat(scrollEl: ScrollFake) {
  const stub = contentStub(scrollEl);
  return shallowMount(TabAiChat, {
    props: { aiConversationId: 'conv-1', userName: 'leo' },
    ...mountOptions(stub),
  });
}

function refresherEvent() {
  return { target: { complete: vi.fn() } };
}

beforeEach(() => {
  vi.clearAllMocks();
  api.getChatMessages.mockResolvedValue({ data: [] });
  api.getAiChatMessages.mockResolvedValue({ data: [], has_more: false });
});

describe('chat room pull-to-refresh keeps the viewport still', () => {
  it('compensates the scroll position by the height of the prepended messages', async () => {
    const scrollEl: ScrollFake = { scrollTop: 0, scrollHeight: 500 };
    const wrapper = mountRoom(scrollEl);
    await flushPromises();

    const state = (wrapper.vm as any).$.setupState;
    state.messages.push({ id: 'm2', content: '现有消息', role: '2' });

    api.getChatMessages.mockImplementation(async () => {
      growBy(scrollEl, 300); // 上面多出两条更早的消息
      return {
        data: [
          JSON.stringify({ id: 'm1', content: '更早一条', user_id: 2 }),
          JSON.stringify({ id: 'm2', content: '现有消息', user_id: 2 }),
        ],
      };
    });

    const e = refresherEvent();
    await state.onRefresh(e);
    await flushPromises();

    expect(scrollEl.scrollTop).toBe(300);
    expect(e.target.complete).toHaveBeenCalledOnce();
    wrapper.unmount();
  });

  it('does not scroll when the list was empty before the refresh', async () => {
    const scrollEl: ScrollFake = { scrollTop: 0, scrollHeight: 500 };
    const wrapper = mountRoom(scrollEl);
    await flushPromises();

    const state = (wrapper.vm as any).$.setupState;
    api.getChatMessages.mockImplementation(async () => {
      growBy(scrollEl, 300);
      return { data: [JSON.stringify({ id: 'm1', content: 'a', user_id: 2 })] };
    });

    await state.onRefresh(refresherEvent());
    await flushPromises();

    expect(scrollEl.scrollTop).toBe(0);
    wrapper.unmount();
  });

  it('still completes the refresher when the request fails', async () => {
    const scrollEl: ScrollFake = { scrollTop: 0, scrollHeight: 500 };
    const wrapper = mountRoom(scrollEl);
    await flushPromises();

    const state = (wrapper.vm as any).$.setupState;
    state.messages.push({ id: 'm2', content: '现有消息', role: '2' });
    api.getChatMessages.mockRejectedValue(new Error('boom'));

    const e = refresherEvent();
    await state.onRefresh(e);
    await flushPromises();

    expect(e.target.complete).toHaveBeenCalledOnce();
    expect(scrollEl.scrollTop).toBe(0); // 什么都没插进去，就不该滚
    wrapper.unmount();
  });
});

describe('AI chat pull-to-refresh keeps the viewport still', () => {
  it('compensates the scroll position after loading an older page', async () => {
    const scrollEl: ScrollFake = { scrollTop: 0, scrollHeight: 600 };
    const wrapper = mountAiChat(scrollEl);
    await flushPromises();

    const state = (wrapper.vm as any).$.setupState;
    state.messages.push({ bubbleKey: 'k1', content: '现有消息', role: 'me' });

    api.getAiChatMessages.mockImplementation(async () => {
      growBy(scrollEl, 240);
      return {
        data: [{ id: 'h1', query: '更早的问题', answer: '更早的回答', message_files: [] }],
        has_more: false,
      };
    });

    const e = refresherEvent();
    await state.doRefresh(e);
    await flushPromises();

    expect(scrollEl.scrollTop).toBe(240);
    expect(e.target.complete).toHaveBeenCalledOnce();
    wrapper.unmount();
  });

  it('does not scroll when nothing new was prepended', async () => {
    const scrollEl: ScrollFake = { scrollTop: 0, scrollHeight: 600 };
    const wrapper = mountAiChat(scrollEl);
    await flushPromises();

    const state = (wrapper.vm as any).$.setupState;
    state.messages.push({ bubbleKey: 'k1', content: '现有消息', role: 'me' });
    api.getAiChatMessages.mockResolvedValue({ data: [], has_more: false });

    await state.doRefresh(refresherEvent());
    await flushPromises();

    expect(scrollEl.scrollTop).toBe(0);
    wrapper.unmount();
  });

  it('completes immediately when there is no conversation to load', async () => {
    const scrollEl: ScrollFake = { scrollTop: 0, scrollHeight: 600 };
    const stub = contentStub(scrollEl);
    const wrapper = shallowMount(TabAiChat, {
      props: { aiConversationId: '', userName: 'leo' },
      ...mountOptions(stub),
    });
    await flushPromises();

    const state = (wrapper.vm as any).$.setupState;
    const e = refresherEvent();
    await state.doRefresh(e);

    expect(e.target.complete).toHaveBeenCalledOnce();
    expect(api.getAiChatMessages).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
