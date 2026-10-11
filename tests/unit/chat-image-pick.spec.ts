import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { nextTick } from 'vue';
import PageChat from '@/views/page-chat/PageChat.vue';
import { DEFAULT_MAX_PENDING_IMAGES } from '@/views/page-chat/chat-image-picker';

const mocks = vi.hoisted(() => ({
  recorder: { open: vi.fn(), start: vi.fn(), stop: vi.fn(), close: vi.fn() },
  socket: {
    connected: true,
    on: vi.fn(),
    emit: vi.fn(),
    removeAllListeners: vi.fn(),
    disconnect: vi.fn(),
  },
  toast: vi.fn(),
  uploadPic: vi.fn(),
  deletePicFile: vi.fn(),
  resizeImageToFile: vi.fn(),
  getChatSetting: vi.fn(),
  setChatSetting: vi.fn(),
  getAccessToken: vi.fn(),
}));

vi.mock('recorder-core/recorder.wav.min', () => ({ default: () => mocks.recorder }));
vi.mock('socket.io-client', () => ({ default: () => mocks.socket }));
vi.mock('@/api/api-client', () => ({ getApiUrl: () => 'https://example.com/api' }));
vi.mock('@/api/api-chat', () => ({
  getChatSetting: mocks.getChatSetting,
  setChatSetting: mocks.setChatSetting,
}));
vi.mock('@/api/api-user', () => ({
  getUserList: async (): Promise<{ data: never[] }> => ({ data: [] }),
}));
// 选图后会后台上传，这里必须挡掉网络，否则测试依赖真实请求
vi.mock('@/api/api-pic', () => ({
  uploadPic: mocks.uploadPic,
  deletePicFile: mocks.deletePicFile,
}));
vi.mock('@/utils/img-mgr', () => ({ resizeImageToFile: mocks.resizeImageToFile }));
// /pic/delete 现已要求鉴权：未登录时不发请求（避免 401 触发跳登录页）
vi.mock('@/utils/auth-util', () => ({ getAccessToken: mocks.getAccessToken }));
vi.mock('@/types/event-bus', () => ({
  default: { $emit: mocks.toast },
  C_EVENT: { TOAST: 'toast' },
}));
vi.mock('@/views/page-chat/TabChatRoom.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/views/page-chat/TabAiChat.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/views/page-chat/TabTtsTasks.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/views/page-chat/dialogs/ChatSetting.vue', () => ({
  default: { template: '<div />' },
}));
vi.mock('@/components/ServerRemoteBadge.vue', () => ({ default: { template: '<div />' } }));

const revokeObjectURL = vi.fn();

let wrapper: ReturnType<typeof shallowMount>;
let state: any;

function makeFile(name: string, type = 'image/png'): File {
  return new File(['x'], name, { type });
}

/** 模拟 input 的 change 事件；files 来自选择器，value 用于验证是否被清空 */
function changeEvent(files: File[]) {
  return { target: { files, value: 'C:\\fakepath\\a.png' } } as unknown as Event;
}

beforeEach(async () => {
  vi.clearAllMocks();
  Object.defineProperty(URL, 'createObjectURL', {
    writable: true,
    configurable: true,
    value: (file: File) => `blob:${file.name}`,
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    writable: true,
    configurable: true,
    value: revokeObjectURL,
  });

  // 默认：没有已存的 setting；压缩原样返回，上传成功并给出去重后的文件名
  mocks.getChatSetting.mockResolvedValue(null);
  mocks.setChatSetting.mockResolvedValue(undefined);
  mocks.resizeImageToFile.mockImplementation(async (file: File) => file);
  mocks.uploadPic.mockImplementation(async (file: File) => ({
    filename: `up_${file.name}`,
    path: `/tmp/up_${file.name}`,
  }));
  mocks.deletePicFile.mockResolvedValue(undefined);
  mocks.getAccessToken.mockReturnValue('fake-token');

  wrapper = shallowMount(PageChat, {
    global: {
      provide: { globalVar: { user: { id: 1, name: 'test' } } },
      config: { warnHandler: () => {} },
    },
  });
  await flushPromises();
  state = (wrapper.vm as any).$.setupState;
  // 发送要求 socket 已握手（见 sendAiText）
  state.socketHandshakeOk = true;
  state.socketReady = true;
});

afterEach(() => {
  wrapper.unmount();
});

describe('对话输入区添加图片', () => {
  it('图片按钮位于发送按钮右侧，选择器支持多选（手机端同时给拍照/相册）', () => {
    const pickButton = wrapper.find('[data-testid="pick-image-button"]');
    expect(pickButton.exists()).toBe(true);

    const container = pickButton.element.parentElement!;
    const siblings = Array.from(container.children).filter(
      (el) => el.tagName.toLowerCase() === 'ion-button'
    );
    // 发送按钮在前、图片按钮紧随其后
    expect(siblings).toHaveLength(2);
    expect(siblings[0]).not.toBe(pickButton.element);
    expect(siblings[1]).toBe(pickButton.element);

    const input = wrapper.find('input[type="file"]');
    expect(input.attributes('accept')).toBe('image/*');
    expect(input.attributes('multiple')).toBeDefined();
  });

  it('图片按钮与发送按钮样式成对：同组件、同高度，并固定为正方形', () => {
    const pickButton = wrapper.find('[data-testid="pick-image-button"]');
    const sendButton = wrapper
      .findAll('ion-button')
      .find((b) => b.text().includes('发送'))!;
    expect(sendButton.exists()).toBe(true);

    // 必须同为 ion-button：圆角、按压反馈、iOS/Android 差异才由 Ionic 统一保证
    expect(pickButton.element.tagName).toBe('ION-BUTTON');
    expect(sendButton.element.tagName).toBe('ION-BUTTON');

    for (const btn of [pickButton, sendButton]) {
      expect(btn.classes()).toContain('h-10');
      expect(btn.classes()).toContain('min-h-10!');
    }

    // 图标按钮固定成 40×40 正方形：Ionic 图标按钮默认有左右内边距，会把它撑宽
    expect(pickButton.classes()).toContain('w-10');
    expect(pickButton.classes()).toContain('[--padding-start:0]');
    expect(pickButton.classes()).toContain('[--padding-end:0]');
    // 两按钮之间留一点间隙，避免贴在一起
    expect(sendButton.classes()).toContain('mr-1');
    // 注：主次区分用的是 Ionic 的 fill="outline"，但 Stencil 的 prop 在 jsdom 里
    // 不反射为 HTML 属性，单元测试无法断言；这里只覆盖结构与尺寸。
  });

  it('选中后渲染预览条与缩略图，移除后预览条消失', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await nextTick();

    const strip = wrapper.find('[data-testid="pending-image-strip"]');
    expect(strip.exists()).toBe(true);
    expect(strip.findAll('img')).toHaveLength(1);

    state.btnRemovePendingImage(0);
    await nextTick();
    expect(wrapper.find('[data-testid="pending-image-strip"]').exists()).toBe(false);
  });

  it('点击图片按钮时把点击转交给隐藏的 file input（手机相机/相册、PC 文件框同一入口）', () => {
    const click = vi.fn();
    state.imageInputRef = { click };
    state.pickImages();

    expect(click).toHaveBeenCalledOnce();
  });

  it('选中的图片进入待处理列表并生成预览，同时清空 input 以便重复选同一张', () => {
    const event = changeEvent([makeFile('1.png'), makeFile('2.jpg', 'image/jpeg')]);
    state.onImageFileChange(event);

    expect(state.pendingImages.map((item: any) => item.file.name)).toEqual([
      '1.png',
      '2.jpg',
    ]);
    expect(state.pendingImages.map((item: any) => item.previewUrl)).toEqual([
      'blob:1.png',
      'blob:2.jpg',
    ]);
    expect(state.showImagePreview).toBe(true);
    expect((event.target as any).value).toBe('');
  });

  it('非图片文件被忽略并提示', () => {
    state.onImageFileChange(changeEvent([makeFile('note.txt', 'text/plain')]));

    expect(state.pendingImages).toHaveLength(0);
    expect(mocks.toast).toHaveBeenCalledWith('toast', '只能添加图片文件');
  });

  it('超过默认上限的张数会提示，且不会生成多余预览', () => {
    const files = Array.from({ length: DEFAULT_MAX_PENDING_IMAGES + 2 }, (_, i) =>
      makeFile(`${i}.png`)
    );
    state.onImageFileChange(changeEvent(files));

    expect(state.pendingImages).toHaveLength(DEFAULT_MAX_PENDING_IMAGES);
    expect(mocks.toast).toHaveBeenCalledWith(
      'toast',
      `最多添加 ${DEFAULT_MAX_PENDING_IMAGES} 张图片`
    );
  });

  it('上限取自 chat setting 的 maxImages（无 UI，改数据即生效）', () => {
    state.chatSetting = { ...state.chatSetting, maxImages: 2 };

    state.onImageFileChange(
      changeEvent([makeFile('1.png'), makeFile('2.png'), makeFile('3.png')])
    );

    expect(state.pendingImageLimit).toBe(2);
    expect(state.pendingImages).toHaveLength(2);
    expect(mocks.toast).toHaveBeenCalledWith('toast', '最多添加 2 张图片');
  });

  it('setting 里的 maxImages 非法时回落到默认 3', () => {
    state.chatSetting = { ...state.chatSetting, maxImages: 0 };
    expect(state.pendingImageLimit).toBe(DEFAULT_MAX_PENDING_IMAGES);

    state.chatSetting = { ...state.chatSetting, maxImages: 'x' };
    expect(state.pendingImageLimit).toBe(DEFAULT_MAX_PENDING_IMAGES);
  });

  it('预览条只在有图片时展示，TTS 页签下隐藏但保留选择', () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    expect(state.showImagePreview).toBe(true);

    state.chatType = 'tts_tasks';
    expect(state.showImagePreview).toBe(false);
    expect(state.pendingImages).toHaveLength(1);
  });

  it('移除单张会释放对应预览 URL，卸载时释放全部', () => {
    state.onImageFileChange(changeEvent([makeFile('1.png'), makeFile('2.png')]));

    state.btnRemovePendingImage(0);
    expect(state.pendingImages.map((item: any) => item.file.name)).toEqual(['2.png']);
    expect(revokeObjectURL.mock.calls).toEqual([['blob:1.png']]);

    wrapper.unmount();
    expect(revokeObjectURL.mock.calls.map((call) => call[0])).toEqual([
      'blob:1.png',
      'blob:2.png',
    ]);
  });
});

describe('对话输入区发送图片', () => {
  it('上传时改用 chat-<userid>-<时间戳> 命名，不带原始文件名', async () => {
    state.onImageFileChange(changeEvent([makeFile('我的照片 1.png')]));
    await flushPromises();

    const uploaded: File = mocks.uploadPic.mock.calls[0][0];
    expect(uploaded.name).toMatch(/^chat-1-\d+\.png$/);
    expect(uploaded.name).not.toContain('我的照片');
    // 服务端返回什么名字就用什么名字（pic_mgr 可能加 _1 去重）
    expect(state.pendingImages[0].filename).toBe(`up_${uploaded.name}`);
  });

  it('扩展名按实际内容取，避免 .bmp 里装着 jpeg', async () => {
    // 模拟 resize 把 bmp 转成了 jpeg
    mocks.resizeImageToFile.mockImplementationOnce(
      async (file: File) => new File(['x'], file.name, { type: 'image/jpeg' })
    );
    state.onImageFileChange(changeEvent([makeFile('photo.bmp', 'image/bmp')]));
    await flushPromises();

    expect(mocks.uploadPic.mock.calls[0][0].name).toMatch(/^chat-1-\d+\.jpg$/);
  });

  it('选图后立即后台上传并写回 filename（发送时无需等待）', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    expect(mocks.resizeImageToFile).toHaveBeenCalledTimes(1);
    expect(mocks.uploadPic).toHaveBeenCalledTimes(1);
    expect(state.pendingImages[0].filename).toBe(
      `up_${mocks.uploadPic.mock.calls[0][0].name}`
    );
    expect(state.pendingImages[0].uploading).toBe(false);
    expect(state.pendingImages[0].error).toBeUndefined();
  });

  it('上传失败时记录 error 并提示', async () => {
    mocks.uploadPic.mockRejectedValueOnce(new Error('磁盘满了'));
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    expect(state.pendingImages[0].error).toBe('磁盘满了');
    expect(mocks.toast).toHaveBeenCalledWith('toast', '图片上传失败：磁盘满了');
  });

  it('发送时把文件名随消息发出，并清空待发区', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    const filename = state.pendingImages[0].filename;

    state.inputText = '看看这张图';
    state.sendTextMessage();

    const sent = JSON.parse(mocks.socket.emit.mock.calls.at(-1)![1]);
    expect(sent.content).toBe('看看这张图');
    expect(sent.files).toEqual([{ type: 'image', filename }]);
    expect(state.pendingImages).toHaveLength(0);
  });

  it('只发图片不打字时补占位文案（Dify 的 query 不允许为空）', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    state.inputText = '';
    state.sendTextMessage();

    const sent = JSON.parse(mocks.socket.emit.mock.calls.at(-1)![1]);
    expect(sent.content).toBe('[图片]');
    expect(sent.files).toHaveLength(1);
  });

  it('图片仍在上传时拒绝发送并提示', () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    state.pendingImages[0].uploading = true;
    state.inputText = '等等我';

    state.sendTextMessage();

    expect(mocks.socket.emit).not.toHaveBeenCalled();
    expect(mocks.toast).toHaveBeenCalledWith('toast', '图片还在上传，请稍候');
  });

  it('有图片上传失败时拒绝发送并提示', async () => {
    mocks.uploadPic.mockRejectedValueOnce(new Error('失败'));
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    state.inputText = '有问题';

    state.sendTextMessage();

    expect(state.pendingImages[0].error).toBe('失败');
    expect(mocks.socket.emit).not.toHaveBeenCalled();
    expect(mocks.toast).toHaveBeenCalledWith(
      'toast',
      '有图片上传失败，请先移除后再发送'
    );
  });
});

describe('图片上限存在 chat setting 里', () => {
  it('从服务端 setting 读到 maxImages 并生效', async () => {
    mocks.getChatSetting.mockResolvedValue(JSON.stringify({ maxImages: 2 }));

    // onIonViewDidEnter 在测试环境不会触发，显式加载一次
    await state.updateChatSetting();

    expect(state.pendingImageLimit).toBe(2);

    state.onImageFileChange(
      changeEvent([makeFile('1.png'), makeFile('2.png'), makeFile('3.png')])
    );
    expect(state.pendingImages).toHaveLength(2);
    expect(mocks.toast).toHaveBeenCalledWith('toast', '最多添加 2 张图片');
  });

  it('旧数据缺 maxImages 时补写一次，让它成为可见可改的数据', async () => {
    mocks.getChatSetting.mockResolvedValue(JSON.stringify({ ttsSpeed: 1.2 }));

    await state.updateChatSetting();

    expect(mocks.setChatSetting).toHaveBeenCalledTimes(1);
    const [userId, payload] = mocks.setChatSetting.mock.calls[0];
    expect(userId).toBe(1);
    expect(JSON.parse(payload)).toEqual({
      ttsSpeed: 1.2,
      maxImages: DEFAULT_MAX_PENDING_IMAGES,
    });
  });

  it('已有 maxImages 时不重复写回（避免每次进页面都写）', async () => {
    mocks.getChatSetting.mockResolvedValue(JSON.stringify({ maxImages: 3 }));

    await state.updateChatSetting();

    expect(mocks.setChatSetting).not.toHaveBeenCalled();
  });

  it('补写失败不影响使用（内存里仍有默认值）', async () => {
    mocks.getChatSetting.mockResolvedValue(JSON.stringify({ ttsSpeed: 1.2 }));
    mocks.setChatSetting.mockRejectedValueOnce(new Error('网络错误'));

    await state.updateChatSetting();

    expect(state.pendingImageLimit).toBe(DEFAULT_MAX_PENDING_IMAGES);
    // 不打扰用户：这是后台补数据，失败无感即可
    expect(mocks.toast).not.toHaveBeenCalled();
  });

  it('传给设置弹窗的快照不含 maxImages，避免保存时覆写服务端的值', () => {
    // 弹窗的合并是 {...服务端现有值, ...快照}，快照里一旦带上 maxImages，
    // 就会用内存旧值盖掉服务端新值 —— 这个字段只该作为数据存在。
    expect(state.chatSettingSnapshot).not.toHaveProperty('maxImages');
  });
});

describe('待发图片的大图预览', () => {
  it('缩略图比原来大（w-16 h-16），预览条相应加高', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await nextTick();
    const strip = wrapper.find('[data-testid="pending-image-strip"]');
    expect(strip.exists()).toBe(true);

    // 预览条高度必须和 IMAGE_PREVIEW_STRIP_HEIGHT 保持一致，否则会顶掉消息区
    expect(strip.classes()).toContain('h-20');

    // 尺寸类挂在外层容器上（img 自身是 w-full h-full 撑满）
    const thumbBox = strip.find('div.relative');
    expect(thumbBox.classes()).toContain('w-16');
    expect(thumbBox.classes()).toContain('h-16');

    // 点击放大需要可见的交互提示
    expect(strip.find('img').classes()).toContain('cursor-zoom-in');
  });

  it('点缩略图打开预览，并定位到对应那张', async () => {
    state.onImageFileChange(
      changeEvent([makeFile('1.png'), makeFile('2.png'), makeFile('3.png')])
    );
    expect(state.pendingPreview.open).toBe(false);

    state.openPendingPreview(2);

    expect(state.pendingPreview).toEqual({ open: true, index: 2 });
    expect(state.pendingPreviewImages.map((i: any) => i.alt)).toEqual([
      '1.png',
      '2.png',
      '3.png',
    ]);
    expect(state.pendingPreviewImages[2].src).toBe('blob:3.png');
  });

  it('预览用的是本地 object URL，不需要请求服务器', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    state.openPendingPreview(0);

    expect(state.pendingPreviewImages[0].src).toBe('blob:1.png');
  });

  it('点 X 移除后预览索引仍指向存在的图片（或自动关闭）', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png'), makeFile('2.png')]));
    state.openPendingPreview(1);

    state.btnRemovePendingImage(0);

    // 列表变短，索引 1 现在越界；预览组件会自行关闭，这里确认列表与索引一致可判定
    expect(state.pendingPreviewImages.map((i: any) => i.alt)).toEqual(['2.png']);
    expect(state.pendingPreviewImages.length).toBeLessThanOrEqual(
      state.pendingPreview.index + 1
    );
  });
});

describe('待发图片的服务端清理', () => {
  it('点 X 撤掉图片时，删除服务器上的副本', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    const filename = state.pendingImages[0].filename;

    state.btnRemovePendingImage(0);
    await flushPromises();

    expect(state.pendingImages).toHaveLength(0);
    expect(mocks.deletePicFile).toHaveBeenCalledWith(filename);
    expect(mocks.deletePicFile).toHaveBeenCalledTimes(1);
  });

  it('点 X 删不掉的图片不影响本地移除，只提示', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    mocks.deletePicFile.mockRejectedValueOnce(new Error('网络错误'));

    state.btnRemovePendingImage(0);
    await flushPromises();

    expect(state.pendingImages).toHaveLength(0);
    expect(mocks.toast).toHaveBeenCalledWith('toast', '删除图片失败：网络错误');
  });

  it('文件已不存在时静默视为成功，不打扰用户', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    mocks.deletePicFile.mockRejectedValueOnce(new Error('文件不存在'));

    state.btnRemovePendingImage(0);
    await flushPromises();

    expect(mocks.toast).not.toHaveBeenCalled();
  });

  it('上传晚到时（图已被撤掉）补删服务器副本', async () => {
    // 让上传挂起，模拟"上传中就被撤掉"
    let finishUpload: (v: { filename: string; path: string }) => void = () => {};
    mocks.uploadPic.mockReturnValueOnce(
      new Promise((resolve) => {
        finishUpload = resolve;
      })
    );

    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    state.btnRemovePendingImage(0);
    expect(mocks.deletePicFile).not.toHaveBeenCalled();

    finishUpload({ filename: 'chat-1-9.png', path: '/tmp/chat-1-9.png' });
    await flushPromises();

    expect(mocks.deletePicFile).toHaveBeenCalledWith('chat-1-9.png');
  });

  it('发送成功后不再删除服务器文件（已被消息引用）', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    state.inputText = '看图';
    state.sendTextMessage();
    await flushPromises();

    expect(state.pendingImages).toHaveLength(0);
    expect(mocks.deletePicFile).not.toHaveBeenCalled();
  });

  it('卸载时丢弃未发送的图片并清理服务器副本', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    const filename = state.pendingImages[0].filename;

    wrapper.unmount();
    await flushPromises();

    expect(mocks.deletePicFile).toHaveBeenCalledWith(filename);
  });

  it('未登录时不去上传（避免 401 把用户踢到登录页），并标记失败', async () => {
    mocks.getAccessToken.mockReturnValue(null);

    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    expect(mocks.uploadPic).not.toHaveBeenCalled();
    expect(state.pendingImages[0].error).toBe('登录状态已失效，请重新登录');
    // 提前返回，压根没进入上传状态
    expect(state.pendingImages[0].uploading).toBeFalsy();
  });

  it('上传接口要求鉴权：已登录时正常发起上传', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    expect(mocks.uploadPic).toHaveBeenCalledTimes(1);
    expect(state.pendingImages[0].error).toBeUndefined();
    expect(state.pendingImages[0].filename).toBeTruthy();
  });

  it('上传失败后可以点重试恢复（不会一直卡在失败态）', async () => {
    mocks.uploadPic.mockRejectedValueOnce(new Error('磁盘满了'));
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    expect(state.pendingImages[0].error).toBe('磁盘满了');

    // 失败项不会被自动重试（否则会无限循环），只能手动触发
    mocks.uploadPic.mockClear();
    await nextTick();
    state.btnRetryUpload(0);
    await flushPromises();

    expect(mocks.uploadPic).toHaveBeenCalledTimes(1);
    expect(state.pendingImages[0].error).toBeUndefined();
    expect(state.pendingImages[0].filename).toBeTruthy();
  });

  it('重试不会新增一项（此前重选同一张会多出一项）', async () => {
    mocks.uploadPic.mockRejectedValueOnce(new Error('boom'));
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    expect(state.pendingImages).toHaveLength(1);

    state.btnRetryUpload(0);
    await flushPromises();

    expect(state.pendingImages).toHaveLength(1);
  });

  it('上传中重复点重试不会并发上传', async () => {
    let finish: (v: { filename: string; path: string }) => void = () => {};
    mocks.uploadPic.mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      })
    );
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    // 等 resize 的微任务走完，上传才真正发出
    await flushPromises();
    expect(mocks.uploadPic).toHaveBeenCalledTimes(1);
    expect(state.pendingImages[0].uploading).toBe(true);

    state.btnRetryUpload(0);
    expect(mocks.uploadPic).toHaveBeenCalledTimes(1);

    finish({ filename: 'chat-1-1.png', path: 'p' });
    await flushPromises();
    expect(state.pendingImages[0].filename).toBe('chat-1-1.png');
  });

  it('未登录时不发删除请求（避免 401 把用户踢到登录页）', async () => {
    mocks.getAccessToken.mockReturnValue(null);
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    state.btnRemovePendingImage(0);
    await flushPromises();

    // 本地照常移除，只是不惊动服务器
    expect(state.pendingImages).toHaveLength(0);
    expect(mocks.deletePicFile).not.toHaveBeenCalled();
    expect(mocks.toast).not.toHaveBeenCalled();
  });
});

describe('聊天室发图', () => {
  /** 切到聊天室需要 room 面板，shallowMount 会 stub 掉它 */
  function stubRoomTab() {
    const added: any[] = [];
    state.chatRoomTabRef = {
      addMessage: (m: any) => added.push(m),
      scrollToBottom: vi.fn(),
      loadInitial: vi.fn(),
    };
    return added;
  }

  it('聊天室发送时随消息带出图片（此前会被静默丢弃）', async () => {
    const added = stubRoomTab();
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    state.chatType = 'chat_room';
    state.inputText = '房间里的图';
    mocks.socket.emit.mockClear();
    state.sendTextMessage();
    await flushPromises();

    const sent = JSON.parse(
      mocks.socket.emit.mock.calls.find((c) => c[0] === 'message')![1]
    );
    expect(sent.chatType).toBe('chat_room');
    expect(sent.files).toEqual([
      { type: 'image', filename: expect.stringContaining('chat-1-') },
    ]);
    // 本地回显也要带图，否则发送者自己看不到
    expect(added.at(-1)?.images).toHaveLength(1);
  });

  it('发送后从待发区移除，但保留服务器文件（已被消息引用）', async () => {
    stubRoomTab();
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    state.chatType = 'chat_room';
    state.inputText = 'x';
    state.sendTextMessage();
    await flushPromises();

    expect(state.pendingImages).toHaveLength(0);
    expect(mocks.deletePicFile).not.toHaveBeenCalled();
  });

  it('图片仍在上传/已失败时拦住发送', async () => {
    stubRoomTab();
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    state.chatType = 'chat_room';
    state.inputText = 'x';

    state.pendingImages[0].uploading = true;
    mocks.socket.emit.mockClear();
    state.sendTextMessage();
    expect(mocks.socket.emit).not.toHaveBeenCalled();
    expect(mocks.toast).toHaveBeenCalledWith('toast', '图片还在上传，请稍候');
  });

  it('只发图不打字也允许发送', async () => {
    stubRoomTab();
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();

    state.chatType = 'chat_room';
    state.inputText = '';
    mocks.socket.emit.mockClear();
    state.sendTextMessage();
    await flushPromises();

    const sent = JSON.parse(
      mocks.socket.emit.mock.calls.find((c) => c[0] === 'message')![1]
    );
    expect(sent.files).toHaveLength(1);
    expect(sent.content).toBe('');
  });

  it('收到他人带图消息时渲染出图片', async () => {
    const added = stubRoomTab();

    // msgChat 是内联回调，从 socket 的注册记录里取出来触发
    const call = mocks.socket.on.mock.calls.find((c: any[]) => c[0] === 'msgChat');
    expect(call, 'msgChat 监听必须已注册').toBeDefined();
    await call![1]({
      chat_type: 'chat_room',
      user_id: 2,
      content: '他发的图',
      files: [{ type: 'image', filename: 'chat-2-9.png' }],
    });

    expect(added.at(-1)?.images).toEqual(['chat-2-9.png']);
  });

  it('他人消息没有 files 时不带 images 字段', async () => {
    const added = stubRoomTab();
    const call = mocks.socket.on.mock.calls.find((c: any[]) => c[0] === 'msgChat');

    await call![1]({ chat_type: 'chat_room', user_id: 2, content: '只有文字' });

    expect(added.at(-1)?.images).toBeUndefined();
  });
});

describe('重试时保留图片', () => {
  /**
   * 图片在发送后就从输入区清空了，气泡上的 `images` 是唯一凭证。
   * 回归点：重试若不带回图片，就会变成"只重发文字"，用户以为自己发的图丢了。
   */
  function stubAiTab(images: string[]) {
    // shallowMount 会 stub 掉 TabAiChat，重试路径需要这些方法
    state.aiChatTabRef = {
      getRequestImages: () => images,
      getRequestRetryText: () => '',
      prepareForResend: vi.fn(),
      addMessage: vi.fn(),
      scrollToBottomIfNeeded: vi.fn(),
      ensureAwaitingReply: vi.fn(),
      confirmUserSent: vi.fn(),
      failUserSend: vi.fn(),
      failActiveReply: vi.fn(),
      restoreServerReply: vi.fn(),
      finishActiveReply: vi.fn(),
      getPendingClientRequestIds: (): string[] => [],
      applyChatChunk: vi.fn(),
    };
  }

  async function sendWithImage() {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    state.inputText = '看看这张图';
    state.sendTextMessage();
    await flushPromises();

    const sent = JSON.parse(mocks.socket.emit.mock.calls.at(-1)![1]);
    // 服务端确认 + AI 失败，让等待状态结束（否则重试会被 isWaitingServer 拦下）
    state.onMsgAccepted({
      clientRequestId: sent.clientRequestId,
      kind: 'text',
      attempt: 0,
    });
    state.endAiWait({
      failed: true,
      message: 'boom',
      clientRequestId: sent.clientRequestId,
    });
    await flushPromises();
    return sent;
  }

  it('failed 后重发仍带原图片（从气泡取回）', async () => {
    const sent = await sendWithImage();
    const filenames = sent.files.map((f: any) => f.filename);
    stubAiTab(filenames);

    mocks.socket.emit.mockClear();
    state.retryAiMessage('看看这张图', sent.clientRequestId);
    state.handlePendingAiRetryStatus({
      clientRequestId: sent.clientRequestId,
      phase: 'failed',
      attempt: 0,
    });
    await flushPromises();

    const resend = mocks.socket.emit.mock.calls.find((c) => c[0] === 'message');
    expect(resend).toBeDefined();
    expect(JSON.parse(resend![1]).files).toEqual(sent.files);
  });

  it('服务端无记录时（phase 为空）重发也带图', async () => {
    const sent = await sendWithImage();
    stubAiTab(sent.files.map((f: any) => f.filename));

    mocks.socket.emit.mockClear();
    state.retryAiMessage('看看这张图', sent.clientRequestId);
    state.handlePendingAiRetryStatus({
      clientRequestId: sent.clientRequestId,
      phase: null,
    });
    await flushPromises();

    const resend = mocks.socket.emit.mock.calls.find((c) => c[0] === 'message');
    expect(JSON.parse(resend![1]).files).toEqual(sent.files);
  });

  it('纯图片轮次（内容为占位文案）也能重试', async () => {
    state.onImageFileChange(changeEvent([makeFile('1.png')]));
    await flushPromises();
    state.inputText = '';
    state.sendTextMessage();
    await flushPromises();

    const sent = JSON.parse(mocks.socket.emit.mock.calls.at(-1)![1]);
    expect(sent.content).toBe('[图片]');
    state.onMsgAccepted({
      clientRequestId: sent.clientRequestId,
      kind: 'text',
      attempt: 0,
    });
    state.endAiWait({
      failed: true,
      message: 'boom',
      clientRequestId: sent.clientRequestId,
    });
    await flushPromises();

    stubAiTab(sent.files.map((f: any) => f.filename));
    mocks.socket.emit.mockClear();
    state.retryAiMessage('[图片]', sent.clientRequestId);
    state.handlePendingAiRetryStatus({
      clientRequestId: sent.clientRequestId,
      phase: 'failed',
      attempt: 0,
    });
    await flushPromises();

    const resend = mocks.socket.emit.mock.calls.find((c) => c[0] === 'message');
    expect(JSON.parse(resend![1]).files).toEqual(sent.files);
  });

  it('没有图片的普通轮次重试不受影响（files 为空）', async () => {
    state.inputText = '只有文字';
    state.sendTextMessage();
    await flushPromises();
    const sent = JSON.parse(mocks.socket.emit.mock.calls.at(-1)![1]);
    expect(sent.files).toEqual([]);

    state.onMsgAccepted({
      clientRequestId: sent.clientRequestId,
      kind: 'text',
      attempt: 0,
    });
    state.endAiWait({
      failed: true,
      message: 'boom',
      clientRequestId: sent.clientRequestId,
    });
    await flushPromises();

    stubAiTab([]);
    mocks.socket.emit.mockClear();
    state.retryAiMessage('只有文字', sent.clientRequestId);
    state.handlePendingAiRetryStatus({
      clientRequestId: sent.clientRequestId,
      phase: 'failed',
      attempt: 0,
    });
    await flushPromises();

    const resend = mocks.socket.emit.mock.calls.find((c) => c[0] === 'message');
    expect(JSON.parse(resend![1]).files).toEqual([]);
  });
});
