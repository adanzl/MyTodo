import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';
import PageChat from '@/views/page-chat/PageChat.vue';

const mocks = vi.hoisted(() => ({
  recorder: { open: vi.fn(), start: vi.fn(), stop: vi.fn(), close: vi.fn() },
  socket: { connected: true, on: vi.fn(), emit: vi.fn(), removeAllListeners: vi.fn(), disconnect: vi.fn() },
  toast: vi.fn(),
}));
vi.mock('recorder-core/recorder.wav.min', () => ({ default: () => mocks.recorder }));
vi.mock('socket.io-client', () => ({ default: () => mocks.socket }));
vi.mock('@/api/api-client', () => ({ getApiUrl: () => 'https://example.com/api' }));
vi.mock('@/api/api-chat', () => ({
  getChatSetting: async (): Promise<null> => null,
  setChatSetting: vi.fn(),
}));
vi.mock('@/api/api-user', () => ({
  getUserList: async (): Promise<{ data: never[] }> => ({ data: [] }),
}));
vi.mock('@/types/event-bus', () => ({ default: { $emit: mocks.toast }, C_EVENT: { TOAST: 'toast' } }));
vi.mock('@/views/page-chat/TabChatRoom.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/views/page-chat/TabAiChat.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/views/page-chat/TabTtsTasks.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/views/page-chat/dialogs/ChatSetting.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/components/ServerRemoteBadge.vue', () => ({ default: { template: '<div />' } }));

let wrapper: ReturnType<typeof shallowMount>;
let state: any;
function pointer(type: string, id = 1) {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.assign(event, { pointerId: id, isPrimary: true, button: 0 });
  return event;
}

beforeEach(async () => {
  vi.clearAllMocks();
  vi.stubGlobal('isSecureContext', true);
  wrapper = shallowMount(PageChat, {
    global: {
      provide: { globalVar: { user: { id: 1, name: 'test' } } },
      config: { warnHandler: () => {} },
    },
  });
  await flushPromises();
  state = (wrapper.vm as any).$.setupState;
});
afterEach(() => {
  wrapper.unmount();
  vi.unstubAllGlobals();
});

describe('chat recording', () => {
  it('explains why a LAN HTTP page cannot open the microphone', () => {
    vi.stubGlobal('isSecureContext', false);
    state.startRecording(pointer('pointerdown'));
    expect(mocks.recorder.open).not.toHaveBeenCalled();
    expect(mocks.toast).toHaveBeenCalledWith('toast', expect.stringContaining('HTTPS'));
  });

  it('does not start after release while microphone permission is pending', () => {
    state.startRecording(pointer('pointerdown'));
    window.dispatchEvent(pointer('pointerup'));
    mocks.recorder.open.mock.calls[0][0]();
    expect(mocks.recorder.start).not.toHaveBeenCalled();
    expect(mocks.recorder.close).toHaveBeenCalled();
  });

  it('stops once when the active finger is released outside the button', () => {
    state.startRecording(pointer('pointerdown'));
    mocks.recorder.open.mock.calls[0][0]();
    window.dispatchEvent(pointer('pointerup', 2));
    expect(mocks.recorder.stop).not.toHaveBeenCalled();
    window.dispatchEvent(pointer('pointerup'));
    window.dispatchEvent(pointer('pointerup'));
    expect(mocks.recorder.start).toHaveBeenCalledOnce();
    expect(mocks.recorder.stop).toHaveBeenCalledOnce();
    // Even a failed/too-short stop must release the microphone and reset the stream.
    mocks.recorder.stop.mock.calls[0][1]('too short');
    expect(mocks.recorder.close).toHaveBeenCalled();
    expect(mocks.socket.emit).toHaveBeenCalledWith('message', expect.stringContaining('"cancel":true'));
  });

  it('shows permission denial and allows a new attempt', () => {
    state.startRecording(pointer('pointerdown'));
    mocks.recorder.open.mock.calls[0][1]('denied', true);
    expect(mocks.toast).toHaveBeenCalledWith('toast', expect.stringContaining('麦克风权限被拒绝'));
    state.startRecording(pointer('pointerdown'));
    expect(mocks.recorder.open).toHaveBeenCalledTimes(2);
    mocks.recorder.open.mock.calls[1][1]('denied', true);
  });

  it('ignores repeated presses during permission request and closes after unmount', () => {
    state.startRecording(pointer('pointerdown'));
    state.startRecording(pointer('pointerdown'));
    expect(mocks.recorder.open).toHaveBeenCalledOnce();
    wrapper.unmount();
    mocks.recorder.open.mock.calls[0][0]();
    expect(mocks.recorder.start).not.toHaveBeenCalled();
    expect(mocks.recorder.close).toHaveBeenCalled();
  });
});
