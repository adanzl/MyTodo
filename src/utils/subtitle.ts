/**
 * 视频字幕：通过 /media/subtitle/get 获取 sidecar 列表，加载 VTT / SRT（SRT 转 VTT blob）
 */
import { apiClient } from '@/api/api-client';
import { getMediaFileUrl } from '@/utils/file';

export interface ResolvedSubtitleTrack {
  src: string;
  label: string;
  lang: string;
  /** blob URL 需在卸载时 revoke */
  isBlob: boolean;
}

interface SubtitleTrack {
  path: string;
  label: string;
  lang: string;
  ext: 'vtt' | 'srt';
}

/** SRT → WebVTT（HTML5 track 仅原生支持 VTT） */
export function srtToVtt(srt: string): string {
  const normalized = srt.replace(/\r\n/g, '\n').trim();
  if (!normalized) return 'WEBVTT\n\n';

  const cues: string[] = [];
  for (const block of normalized.split(/\n\n+/)) {
    const lines = block.split('\n').map((l) => l.trimEnd()).filter(Boolean);
    if (lines.length < 2) continue;

    const timeIdx = /^\d+$/.test(lines[0].trim()) ? 1 : 0;
    if (timeIdx >= lines.length || !lines[timeIdx].includes('-->')) continue;

    cues.push(`${lines[timeIdx].replace(/,/g, '.')}\n${lines.slice(timeIdx + 1).join('\n')}`);
  }

  return `WEBVTT\n\n${cues.join('\n\n')}\n`;
}

function parseSubtitleTrack(raw: unknown): SubtitleTrack | null {
  if (!raw || typeof raw !== 'object') return null;
  const item = raw as Record<string, unknown>;
  const path = String(item.path ?? '');
  if (!path) return null;

  const ext = String(item.ext ?? path.split('.').pop() ?? '').toLowerCase();
  if (ext !== 'vtt' && ext !== 'srt') return null;

  return {
    path,
    label: String(item.label ?? path),
    lang: String(item.lang ?? 'und'),
    ext,
  };
}

async function fetchSubtitleTracks(videoPath: string): Promise<SubtitleTrack[]> {
  const { data: body } = await apiClient.get('/media/subtitle/get', {
    params: { video_path: videoPath },
  });
  if (!body || body.code !== 0) {
    throw new Error(body?.msg || '获取字幕列表失败');
  }

  const tracks = body.data?.tracks;
  if (!Array.isArray(tracks)) return [];

  return tracks.map(parseSubtitleTrack).filter((t): t is SubtitleTrack => t !== null);
}

async function loadSubtitleTrack(
  track: SubtitleTrack,
  getUrl: (path: string) => string,
): Promise<ResolvedSubtitleTrack | null> {
  const url = getUrl(track.path);
  if (!url) return null;

  const base = { label: track.label, lang: track.lang };
  if (track.ext === 'vtt') {
    return { src: url, ...base, isBlob: false };
  }

  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch subtitle: ${res.status}`);
  const blob = new Blob([srtToVtt(await res.text())], { type: 'text/vtt' });
  return { src: URL.createObjectURL(blob), ...base, isBlob: true };
}

/** 拉取并加载视频可用字幕轨 */
export async function resolveSubtitleTracks(
  videoPath: string,
  getUrl: (path: string) => string = getMediaFileUrl,
): Promise<ResolvedSubtitleTrack[]> {
  if (!videoPath) return [];

  let tracks: SubtitleTrack[];
  try {
    tracks = await fetchSubtitleTracks(videoPath);
  } catch (e) {
    console.warn('获取字幕列表失败:', e);
    return [];
  }

  const resolved: ResolvedSubtitleTrack[] = [];
  for (const track of tracks) {
    try {
      const item = await loadSubtitleTrack(track, getUrl);
      if (item) resolved.push(item);
    } catch (e) {
      console.warn('加载字幕失败:', track.path, e);
    }
  }
  return resolved;
}

export function revokeSubtitleTracks(tracks: ResolvedSubtitleTrack[]) {
  for (const track of tracks) {
    if (track.isBlob) URL.revokeObjectURL(track.src);
  }
}

export function applySubtitleTrack(video: HTMLVideoElement | null, trackIndex: number) {
  if (!video) return;
  for (let i = 0; i < video.textTracks.length; i++) {
    video.textTracks[i].mode = i === trackIndex ? 'showing' : 'hidden';
  }
}

export function hideAllSubtitleTracks(video: HTMLVideoElement | null) {
  if (!video) return;
  for (let i = 0; i < video.textTracks.length; i++) {
    video.textTracks[i].mode = 'hidden';
  }
}
