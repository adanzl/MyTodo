/**
 * 视频字幕工具：支持 VTT / SRT，以及 material.data 配置与同名 sidecar 文件自动发现
 */
import { getMediaFileUrl } from '@/utils/file';

export interface SubtitleSource {
  path: string;
  label?: string;
  lang?: string;
}

export interface ResolvedSubtitleTrack {
  src: string;
  label: string;
  lang: string;
  /** 是否为 blob URL，卸载时需 revoke */
  isBlob: boolean;
}

export interface MaterialSubtitleData {
  subtitleList?: SubtitleSource[];
}

const SIDECAR_SUFFIXES = ['', '.zh', '.chs', '.cht', '.en', '.eng'];
const SUBTITLE_EXTENSIONS = ['.vtt', '.srt'];

/** 根据视频路径推测同目录 sidecar 字幕文件 */
export function guessSidecarSubtitlePaths(videoPath: string): string[] {
  const lastDot = videoPath.lastIndexOf('.');
  if (lastDot <= 0) return [];

  const base = videoPath.slice(0, lastDot);
  const paths: string[] = [];
  for (const suffix of SIDECAR_SUFFIXES) {
    for (const ext of SUBTITLE_EXTENSIONS) {
      paths.push(`${base}${suffix}${ext}`);
    }
  }
  return paths;
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

/** SRT → WebVTT（HTML5 track 仅原生支持 VTT） */
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

async function probeMediaExists(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { method: 'HEAD' });
    return res.ok;
  } catch {
    return false;
  }
}

async function fetchSubtitleText(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch subtitle: ${res.status}`);
  }
  return res.text();
}

function collectSubtitleSources(
  videoPath: string,
  materialData?: MaterialSubtitleData | null
): SubtitleSource[] {
  const seen = new Set<string>();
  const sources: SubtitleSource[] = [];

  const add = (source: SubtitleSource) => {
    const key = source.path;
    if (!key || seen.has(key)) return;
    seen.add(key);
    sources.push(source);
  };

  for (const item of materialData?.subtitleList || []) {
    if (item?.path) add(item);
  }

  for (const path of guessSidecarSubtitlePaths(videoPath)) {
    add({ path, label: labelFromPath(path), lang: langFromPath(path) });
  }

  return sources;
}

/**
 * 解析并加载视频可用字幕轨
 */
export async function resolveSubtitleTracks(
  videoPath: string,
  materialData?: MaterialSubtitleData | null,
  getUrl: (path: string) => string = getMediaFileUrl
): Promise<ResolvedSubtitleTrack[]> {
  if (!videoPath) return [];

  const sources = collectSubtitleSources(videoPath, materialData);
  const resolved: ResolvedSubtitleTrack[] = [];

  for (const source of sources) {
    const url = getUrl(source.path);
    if (!url) continue;

    const ext = source.path.split('.').pop()?.toLowerCase();
    if (ext !== 'vtt' && ext !== 'srt') continue;

    const exists = await probeMediaExists(url);
    if (!exists) continue;

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

/** 切换 video 元素上的字幕显示 */
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
