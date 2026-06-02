/**
 * 视频字幕工具：支持 VTT / SRT，通过 /media/subtitle/get 发现同目录 sidecar 字幕
 */
import { api } from '@/api/config';
import { getMediaFileUrl } from '@/utils/file';

export interface SubtitleSource {
  path: string;
  label?: string;
  lang?: string;
  ext?: string;
}

export interface ResolvedSubtitleTrack {
  src: string;
  label: string;
  lang: string;
  isBlob: boolean;
}

function fileNameFromPath(filePath: string): string {
  const parts = filePath.split(/[/\\]/);
  return parts[parts.length - 1] || filePath;
}

function labelFromPath(filePath: string): string {
  const name = fileNameFromPath(filePath);
  const dot = name.lastIndexOf('.');
  return dot > 0 ? name.slice(0, dot) : name;
}

function langFromPath(filePath: string): string {
  const name = fileNameFromPath(filePath).toLowerCase();
  if (/\.(zh|chs|cht)\./.test(name) || name.includes('.zh.')) return 'zh';
  if (/\.(en|eng)\./.test(name) || name.includes('.en.')) return 'en';
  return 'und';
}

export function srtToVtt(srt: string): string {
  const normalized = srt.replace(/\r\n/g, '\n').trim();
  if (!normalized) return 'WEBVTT\n\n';

  const blocks = normalized.split(/\n\n+/);
  const cues: string[] = [];

  for (const block of blocks) {
    const lines = block.split('\n').map((l) => l.trimEnd()).filter((l) => l.length > 0);
    if (lines.length < 2) continue;

    let timeIdx = 0;
    if (/^\d+$/.test(lines[0].trim())) {
      timeIdx = 1;
    }
    if (timeIdx >= lines.length) continue;

    const timeLine = lines[timeIdx];
    if (!timeLine.includes('-->')) continue;

    const text = lines.slice(timeIdx + 1).join('\n');
    const time = timeLine.replace(/,/g, '.');
    cues.push(`${time}\n${text}`);
  }

  return `WEBVTT\n\n${cues.join('\n\n')}\n`;
}

async function fetchSubtitleText(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch subtitle: ${res.status}`);
  }
  return res.text();
}

export interface SubtitleSearchRow {
  id: string;
  language: string;
  release: string;
  fileName: string;
  fileId: number | null;
}

export interface SubtitleSearchResult {
  mode?: string;
  total_count: number;
  total_pages: number;
  page: number;
  per_page?: number;
  data: SubtitleSearchRow[];
  query?: string;
  video_path?: string;
}

export function parseSubtitleSearchRows(items: unknown[]): SubtitleSearchRow[] {
  if (!Array.isArray(items)) return [];
  const rows: SubtitleSearchRow[] = [];
  for (const item of items) {
    const raw = item as Record<string, unknown>;
    const attrs = raw.attributes as Record<string, unknown> | undefined;
    if (!attrs) continue;
    const files = attrs.files as Array<Record<string, unknown>> | undefined;
    const file = files?.[0];
    const feature = attrs.feature_details as Record<string, unknown> | undefined;
    rows.push({
      id: String(raw.id ?? attrs.subtitle_id ?? ''),
      language: String(attrs.language ?? ''),
      release: String(attrs.release ?? feature?.title ?? ''),
      fileName: String(file?.file_name ?? ''),
      fileId: typeof file?.file_id === 'number' ? file.file_id : null,
    });
  }
  return rows;
}

export async function searchSubtitles(params: {
  mode: 'text' | 'hash';
  video_path?: string;
  query?: string;
  page?: number;
  languages?: string;
}): Promise<SubtitleSearchResult> {
  const rsp = await api.get('/media/subtitle/search', {
    params: {
      mode: params.mode,
      video_path: params.video_path,
      query: params.query,
      page: params.page ?? 1,
      languages: params.languages,
    },
  });
  const body = rsp.data;
  if (!body || body.code !== 0) {
    throw new Error(body?.msg || '字幕搜索失败');
  }
  const payload = body.data ?? {};
  const rawList = Array.isArray(payload.data) ? payload.data : [];
  return {
    mode: payload.mode,
    total_count: Number(payload.total_count ?? 0),
    total_pages: Number(payload.total_pages ?? 0),
    page: Number(payload.page ?? 1),
    per_page: payload.per_page,
    query: payload.query,
    video_path: payload.video_path,
    data: parseSubtitleSearchRows(rawList),
  };
}

export async function listSidecarSubtitles(videoPath: string): Promise<SubtitleSource[]> {
  const rsp = await api.get('/media/subtitle/get', {
    params: { video_path: videoPath },
  });
  const body = rsp.data;
  if (!body || body.code !== 0) {
    throw new Error(body?.msg || '获取字幕列表失败');
  }
  const tracks = body?.data?.tracks;
  if (!Array.isArray(tracks)) return [];
  return tracks
    .map((t: any) => ({
      path: String(t.path || ''),
      label: t.label ? String(t.label) : undefined,
      lang: t.lang ? String(t.lang) : undefined,
      ext: t.ext ? String(t.ext) : undefined,
    }))
    .filter((t) => !!t.path);
}

export async function resolveSubtitleTracks(
  videoPath: string,
  getUrl: (path: string) => string = getMediaFileUrl
): Promise<ResolvedSubtitleTrack[]> {
  if (!videoPath) return [];

  let sources: SubtitleSource[] = [];
  try {
    sources = await listSidecarSubtitles(videoPath);
  } catch (e) {
    console.warn('获取字幕列表失败:', e);
    return [];
  }

  const resolved: ResolvedSubtitleTrack[] = [];

  for (const source of sources) {
    const url = getUrl(source.path);
    if (!url) continue;

    const ext = (source.ext || source.path.split('.').pop() || '').toLowerCase();
    if (ext !== 'vtt' && ext !== 'srt') continue;

    const label = source.label || labelFromPath(source.path);
    const lang = source.lang || langFromPath(source.path);

    try {
      if (ext === 'vtt') {
        resolved.push({ src: url, label, lang, isBlob: false });
      } else {
        const text = await fetchSubtitleText(url);
        const blob = new Blob([srtToVtt(text)], { type: 'text/vtt' });
        resolved.push({
          src: URL.createObjectURL(blob),
          label,
          lang,
          isBlob: true,
        });
      }
    } catch (e) {
      console.warn('加载字幕失败:', source.path, e);
    }
  }

  return resolved;
}

export function revokeSubtitleTracks(tracks: ResolvedSubtitleTrack[]) {
  for (const track of tracks) {
    if (track.isBlob) {
      URL.revokeObjectURL(track.src);
    }
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
