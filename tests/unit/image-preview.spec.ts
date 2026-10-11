import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import ImagePreview from '@/components/ImagePreview.vue';
import { useImagePreview } from '@/views/page-chat/use-image-preview';

/**
 * Ionic 的组件在 jsdom 里是未定义的自定义元素，不会渲染插槽内容。
 * 这里把 ion-modal 换成"渲染插槽的 div"，让浮层里的普通元素（img / button）可被断言。
 */
const slotStub = { template: '<div><slot /></div>' };
const ionicStubs = {
  IonModal: slotStub,
  IonIcon: { template: '<i />' },
};

const IMAGES = [
  { src: 'blob:a.png', alt: 'a.png' },
  { src: 'blob:b.png', alt: 'b.png' },
  { src: 'blob:c.png', alt: 'c.png' },
];

function render(props: Record<string, unknown> = {}) {
  return mount(ImagePreview, {
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

/** 控制按钮是原生 button，直接看 DOM 的 disabled 属性 */
function isDisabled(wrapper: ReturnType<typeof render>, label: string) {
  return (buttonByLabel(wrapper, label)!.element as HTMLButtonElement).disabled;
}

describe('ImagePreview', () => {
  it('renders the image at the given index with its alt text', () => {
    const img = render({ index: 1 }).find('[data-testid="image-preview-img"]');

    expect(img.exists()).toBe(true);
    expect(img.attributes('src')).toBe('blob:b.png');
    expect(img.attributes('alt')).toBe('b.png');
  });

  it('是浮层：不渲染标题栏（ion-header / ion-toolbar / ion-title）', () => {
    const wrapper = render();

    // 用标签查找而非 html() 字符串匹配：html() 会把模板注释也带上，
    // 注释里出现这些字样会造成误报。
    for (const tag of ['ion-header', 'ion-toolbar', 'ion-title']) {
      expect(wrapper.find(tag).exists(), `${tag} 不该存在`).toBe(false);
    }
    // 浮层本体与图片仍在
    expect(wrapper.find('[data-testid="image-preview-body"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="image-preview-img"]').exists()).toBe(true);
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
    const first = render({ index: 0 });
    expect(isDisabled(first, '上一张')).toBe(true);
    expect(isDisabled(first, '下一张')).toBe(false);

    const last = render({ index: 2 });
    expect(isDisabled(last, '上一张')).toBe(false);
    expect(isDisabled(last, '下一张')).toBe(true);
  });

  it('单张图片时不显示翻页控件与计数', () => {
    const wrapper = render({ images: [IMAGES[0]] });

    expect(buttonByLabel(wrapper, '上一张')).toBeUndefined();
    expect(buttonByLabel(wrapper, '下一张')).toBeUndefined();
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

describe('useImagePreview', () => {
  // TabAiChat 与 TabChatRoom 共用它构造预览状态；这里回归的是"文件名 → 可渲染的 src"，
  // 一旦映射写错，两处的预览会同时静默失效（点缩略图没反应或空白）。
  it('把文件名映射成 pic 查看地址，并带上 alt', () => {
    const { imagePreview, openImagePreview } = useImagePreview();

    openImagePreview(['chat-1-1.png', 'chat-1-2.jpg'], 1);

    expect(imagePreview.value.open).toBe(true);
    expect(imagePreview.value.index).toBe(1);
    expect(imagePreview.value.images).toHaveLength(2);
    expect(imagePreview.value.images[1].alt).toBe('chat-1-2.jpg');
    // src 走 pic 查看接口（此处只断言形状，具体 URL 由 getPicDisplayUrl 决定）
    expect(String(imagePreview.value.images[0].src)).toContain('chat-1-1.png');
  });

  it('默认从第一张开始，空列表也能安全打开（由组件自行关闭）', () => {
    const { imagePreview, openImagePreview } = useImagePreview();

    openImagePreview([]);

    expect(imagePreview.value.index).toBe(0);
    expect(imagePreview.value.images).toEqual([]);
  });

  it('初始为关闭状态', () => {
    expect(useImagePreview().imagePreview.value.open).toBe(false);
  });
});
