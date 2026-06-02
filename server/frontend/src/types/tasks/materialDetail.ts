export interface AudioFile {
  id: string;
  name: string;
  duration: string;
  path?: string;
}

export interface Page {
  audioIds: string[];
}

export interface SubtitleFile {
  path: string;
  label?: string;
  lang?: string;
  ext?: string;
}

export interface MaterialDetail {
  pdfLength?: number;
  audioList?: AudioFile[];
  subtitleList?: SubtitleFile[];
  remark?: string;
  pages: Page[];
}
