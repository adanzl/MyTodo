export interface AudioFile {
  id: string;
  name: string;
  duration: string;
  path?: string;
}

export interface Page {
  audioIds: string[];
}

export interface TaskDetail {
  pdfLength?: number;
  audioList?: AudioFile[];
  remark?: string;
  pages: Page[];
}
