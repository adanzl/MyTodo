import { describe, expect, it } from 'vitest';
import { roomImageFilenames } from '@/views/page-chat/chat-room-images';

describe('roomImageFilenames', () => {
  it('reads filenames from the object form used on the wire', () => {
    expect(
      roomImageFilenames([
        { type: 'image', filename: 'chat-1-1.png' },
        { type: 'image', filename: 'chat-1-2.jpg' },
      ])
    ).toEqual(['chat-1-1.png', 'chat-1-2.jpg']);
  });

  it('also accepts a plain string array', () => {
    expect(roomImageFilenames(['chat-1-1.png'])).toEqual(['chat-1-1.png']);
  });

  it('returns an empty array for anything unusable', () => {
    // 一条格式异常的历史消息不该让整个房间加载失败
    expect(roomImageFilenames(undefined)).toEqual([]);
    expect(roomImageFilenames(null)).toEqual([]);
    expect(roomImageFilenames([])).toEqual([]);
    expect(roomImageFilenames('chat-1-1.png')).toEqual([]);
    expect(roomImageFilenames({ filename: 'a.png' })).toEqual([]);
    expect(roomImageFilenames([{}, [], 42, '', '   ', { filename: '' }])).toEqual([]);
  });

  it('trims whitespace and keeps order', () => {
    expect(roomImageFilenames(['  a.png  ', 'b.png'])).toEqual(['a.png', 'b.png']);
  });
});
