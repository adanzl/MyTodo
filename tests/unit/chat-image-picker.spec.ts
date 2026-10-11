import { describe, expect, it, vi } from 'vitest';
import {
  addPendingImages,
  buildChatImageName,
  clearPendingImages,
  DEFAULT_MAX_PENDING_IMAGES,
  discardPendingImages,
  isImageFile,
  normalizeMaxImages,
  removePendingImage,
  type PendingImage,
} from '@/views/page-chat/chat-image-picker';

function makeFile(name: string, type = 'image/png'): File {
  return new File(['x'], name, { type });
}

/** 预览 URL 用文件名代替，便于断言释放的是哪一张 */
const fakeUrl = (file: File) => `blob:${file.name}`;

describe('isImageFile', () => {
  it('accepts image MIME types', () => {
    expect(isImageFile(makeFile('a.png', 'image/png'))).toBe(true);
    expect(isImageFile(makeFile('a.jpg', 'image/jpeg'))).toBe(true);
  });

  it('falls back to the extension when the camera returns an empty MIME', () => {
    expect(isImageFile(makeFile('photo.HEIC', ''))).toBe(true);
    expect(isImageFile(makeFile('photo.jpeg', ''))).toBe(true);
    expect(isImageFile(makeFile('note.txt', ''))).toBe(false);
  });

  it('rejects non-image MIME types even with an image extension', () => {
    expect(isImageFile(makeFile('a.png', 'application/pdf'))).toBe(false);
  });
});

describe('addPendingImages', () => {
  it('keeps the selection order and creates one preview URL per image', () => {
    const list: PendingImage[] = [];
    const result = addPendingImages(
      list,
      [makeFile('1.png'), makeFile('2.png')],
      fakeUrl
    );

    expect(result).toEqual({ added: 2, rejected: 0, overflow: 0 });
    expect(list.map((item) => item.file.name)).toEqual(['1.png', '2.png']);
    expect(list.map((item) => item.previewUrl)).toEqual(['blob:1.png', 'blob:2.png']);
  });

  it('counts rejected non-images and does not preview them', () => {
    const list: PendingImage[] = [];
    const result = addPendingImages(
      list,
      [makeFile('1.png'), makeFile('readme.md', 'text/markdown')],
      fakeUrl
    );

    expect(result).toEqual({ added: 1, rejected: 1, overflow: 0 });
    expect(list).toHaveLength(1);
  });

  it('stops at the default limit and counts the overflow', () => {
    const list: PendingImage[] = [];
    const files = Array.from({ length: DEFAULT_MAX_PENDING_IMAGES + 2 }, (_, i) =>
      makeFile(`${i}.png`)
    );

    const result = addPendingImages(list, files, fakeUrl);

    expect(result).toEqual({
      added: DEFAULT_MAX_PENDING_IMAGES,
      rejected: 0,
      overflow: 2,
    });
    expect(list).toHaveLength(DEFAULT_MAX_PENDING_IMAGES);
  });

  it('honours a custom limit passed in from chat setting', () => {
    const list: PendingImage[] = [];
    const files = Array.from({ length: 5 }, (_, i) => makeFile(`${i}.png`));

    const result = addPendingImages(list, files, fakeUrl, 2);

    expect(result).toEqual({ added: 2, rejected: 0, overflow: 3 });
    expect(list).toHaveLength(2);
  });

  it('falls back to the default when the configured limit is unusable', () => {
    for (const bad of [0, -1, NaN, 'abc', undefined, null]) {
      const list: PendingImage[] = [];
      const files = Array.from({ length: DEFAULT_MAX_PENDING_IMAGES + 1 }, (_, i) =>
        makeFile(`${i}.png`)
      );

      addPendingImages(list, files, fakeUrl, bad as number);

      expect(list).toHaveLength(DEFAULT_MAX_PENDING_IMAGES);
    }
  });

  it('appends to an existing selection', () => {
    const list: PendingImage[] = [{ file: makeFile('old.png'), previewUrl: 'blob:old.png' }];
    addPendingImages(list, [makeFile('new.png')], fakeUrl);

    expect(list.map((item) => item.file.name)).toEqual(['old.png', 'new.png']);
  });
});

describe('removePendingImage', () => {
  it('drops the image and revokes only its preview URL', () => {
    const list: PendingImage[] = [];
    addPendingImages(list, [makeFile('1.png'), makeFile('2.png')], fakeUrl);
    const revoke = vi.fn();

    const removed = removePendingImage(list, 0, revoke);
    // 返回被移除项，调用方需要它的 filename 去删服务器副本
    expect(removed?.previewUrl).toBe('blob:1.png');
    expect(list.map((item) => item.file.name)).toEqual(['2.png']);
    expect(revoke.mock.calls).toEqual([['blob:1.png']]);
    expect(removePendingImage(list, 1, revoke)).toBeUndefined();
  });

  it('ignores an out-of-range index', () => {
    const list: PendingImage[] = [];
    addPendingImages(list, [makeFile('1.png')], fakeUrl);
    const revoke = vi.fn();

    expect(removePendingImage(list, 5, revoke)).toBeUndefined();
    expect(list).toHaveLength(1);
    expect(revoke).not.toHaveBeenCalled();
  });
});

describe('discardPendingImages', () => {
  it('returns uploaded filenames so the server copies can be deleted', () => {
    const list: PendingImage[] = [
      { file: makeFile('1.png'), previewUrl: 'blob:1.png', filename: 'chat-1-1.png' },
      { file: makeFile('2.png'), previewUrl: 'blob:2.png' }, // 还没上传完
    ];
    const revoke = vi.fn();

    expect(discardPendingImages(list, revoke)).toEqual(['chat-1-1.png']);
    expect(list).toHaveLength(0);
    expect(revoke.mock.calls.map((call) => call[0])).toEqual([
      'blob:1.png',
      'blob:2.png',
    ]);
  });

  it('ignores failed uploads that never produced a filename', () => {
    const list: PendingImage[] = [
      { file: makeFile('1.png'), previewUrl: 'blob:1.png', error: '上传失败' },
    ];

    expect(discardPendingImages(list, vi.fn())).toEqual([]);
  });
});

describe('clearPendingImages', () => {
  it('revokes every preview URL and empties the list', () => {
    const list: PendingImage[] = [];
    addPendingImages(list, [makeFile('1.png'), makeFile('2.png')], fakeUrl);
    const revoke = vi.fn();

    expect(clearPendingImages(list, revoke)).toBe(2);
    expect(list).toHaveLength(0);
    expect(revoke.mock.calls.map((call) => call[0])).toEqual([
      'blob:1.png',
      'blob:2.png',
    ]);
  });

  it('is a no-op on an empty selection', () => {
    const list: PendingImage[] = [];
    expect(clearPendingImages(list, vi.fn())).toBe(0);
  });
});

describe('buildChatImageName', () => {
  it('uses the chat-<userid>-<timestamp> format', () => {
    expect(buildChatImageName(7, makeFile('a.png', 'image/png'), 1700)).toBe(
      'chat-7-1700.png'
    );
  });

  it('derives the extension from the actual mime type, not the original name', () => {
    // resize 后内容变成 jpeg，但原始文件名还叫 .bmp
    expect(buildChatImageName(1, makeFile('a.bmp', 'image/jpeg'), 1)).toBe(
      'chat-1-1.jpg'
    );
  });

  it('falls back to the original extension when the mime type is unknown', () => {
    expect(buildChatImageName(1, makeFile('a.JPEG', ''), 1)).toBe('chat-1-1.jpeg');
    expect(buildChatImageName(1, makeFile('noext', ''), 1)).toBe('chat-1-1.jpg');
  });

  it('sanitizes the user id and falls back when it is empty', () => {
    expect(buildChatImageName('a b/c', makeFile('a.png'), 1)).toBe('chat-abc-1.png');
    expect(buildChatImageName('', makeFile('a.png'), 1)).toBe('chat-anon-1.png');
  });
});

describe('normalizeMaxImages', () => {
  it('defaults to 3 when the setting has no usable value', () => {
    expect(DEFAULT_MAX_PENDING_IMAGES).toBe(3);
    for (const bad of [undefined, null, NaN, Infinity, 0, -1, 'abc', {}, []]) {
      expect(normalizeMaxImages(bad)).toBe(DEFAULT_MAX_PENDING_IMAGES);
    }
  });

  it('accepts positive integers and numeric strings', () => {
    expect(normalizeMaxImages(1)).toBe(1);
    expect(normalizeMaxImages(5)).toBe(5);
    // setting 存在 RDS 里的 JSON，数字化字段也可能是字符串
    expect(normalizeMaxImages('4')).toBe(4);
  });

  it('floors fractions rather than rejecting them', () => {
    expect(normalizeMaxImages(2.9)).toBe(2);
    expect(normalizeMaxImages(0.5)).toBe(DEFAULT_MAX_PENDING_IMAGES);
  });
});
