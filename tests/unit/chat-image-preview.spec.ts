import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import ChatImagePreview from '@/views/page-chat/ChatImagePreview.vue';

/**
 * Ionic 的组件在 jsdom 里是未定义的自定义元素，不会渲染插槽内容。
 * 这里把它们替换成"渲染插槽的 div"，让模板里的普通元素（img / 按钮）可被断言，
 * 同时属性会透传到根 div 上，因此仍能按 aria-label 定位按钮。
 */
const slotStub = { template: '<div><slot /></div>' };
const ionicStubs = {
  IonModal: slotStub,
  IonHeader: slotStub,
  IonToolbar: slotStub,
  IonButtons: slotStub,
  IonButton: slotStub,
  IonContent: slotStub,
  IonTitle: slotStub,
};

const IMAGES = [
  { src: 'blob:a.png', alt: 'a.png' },
  { src: 'blob:b.png', alt: 'b.png' },
  { src: 'blob:c.png', alt: 'c.png' },
];

function render(props: Record<string, unknown> = {}) {
  return mount(ChatImagePreview, {
    props: { isOpen: true, images: IMAGES, index: 0, ...props },
    global: {
      stubs: ionicStubs,
      config: { warnHandler: () => {} },
    },
  });
}

function buttonByLabel(wrapper: ReturnType<typeof render>, label: string) {
  return wrapper.findAll('[aria-label]').find((el) => el.attributes('aria-label') === label);
}

describe('ChatImagePreview', () => {
  it('renders the image at the given index with its alt text', () => {
    const img = render({ index: 1 }).find('[data-testid="image-preview-img"]');

    expect(img.exists()).toBe(true);
    expect(img.attributes('src')).toBe('blob:b.png');
    expect(img.attributes('alt')).toBe('b.png');
  });

  it('shows the position counter only when there are multiple images', () => {
    expect(render().text()).toContain('1/3');
    expect(render({ images: [IMAGES[0]] }).text()).not.toContain('1/');
  });

  it('closes when the close button is clicked', async () => {
    const wrapper = render();

    await buttonByLabel(wrapper, '关闭预览')!.trigger('click');

    expect(wrapper.emitted('update:isOpen')).toEqual([[false]]);
  });

  it('closes when the backdrop is clicked but not when the image is clicked', async () => {
    const wrapper = render();

    await wrapper.find('[data-testid="image-preview-img"]').trigger('click');
    expect(wrapper.emitted('update:isOpen')).toBeUndefined();

    await wrapper.find('[data-testid="image-preview-body"]').trigger('click');
    expect(wrapper.emitted('update:isOpen')).toEqual([[false]]);
  });

  it('steps forward and backward through the list', async () => {
    const wrapper = render({ index: 1 });

    await buttonByLabel(wrapper, '下一张')!.trigger('click');
    expect(wrapper.emitted('update:index')).toEqual([[2]]);

    await buttonByLabel(wrapper, '上一张')!.trigger('click');
    expect(wrapper.emitted('update:index')).toEqual([[2], [0]]);
  });

  it('disables navigation at both ends', () => {
    // 经 stub 渲染后 disabled 会落到普通 div 上，值以字符串形式出现
    const isDisabled = (wrapper: ReturnType<typeof render>, label: string) =>
      buttonByLabel(wrapper, label)!.attributes('disabled') === 'true';

    const first = render({ index: 0 });
    expect(isDisabled(first, '上一张')).toBe(true);
    expect(isDisabled(first, '下一张')).toBe(false);

    const last = render({ index: 2 });
    expect(isDisabled(last, '上一张')).toBe(false);
    expect(isDisabled(last, '下一张')).toBe(true);
  });

  it('closes itself when the image list becomes empty (revoked preview URLs)', () => {
    const wrapper = render({ images: [] });

    expect(wrapper.emitted('update:isOpen')).toEqual([[false]]);
  });

  it('closes itself when the index falls out of range after the list shrinks', async () => {
    const wrapper = render({ index: 2 });

    await wrapper.setProps({ images: [IMAGES[0]] });

    expect(wrapper.emitted('update:isOpen')).toEqual([[false]]);
  });
});
