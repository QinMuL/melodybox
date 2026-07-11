// 音乐库相关类型定义

export interface Artist {
  id: string;
  name: string;
  albumCount: number;
  songCount: number;
  coverUrl?: string;
}

export interface Album {
  id: string;
  title: string;
  artistId: string;
  artistName?: string;
  year?: number;
  songCount: number;
  coverUrl?: string;
}

export interface Song {
  id: string;
  albumId: string;
  title: string;
  trackNumber: number;
  duration: number;
  format: string;
  bitrate: number;
  sampleRate: number;
  channels: number;
  filePath: string;
  fileSize: number;
  artist?: string;
  album?: string;
}

export interface LibraryStats {
  totalSongs: number;
  totalArtists: number;
  totalAlbums: number;
  totalDuplicates: number;
  totalSize: number;
  formatBreakdown: { format: string; count: number }[];
}

export interface OrganizeConfig {
  inputDir: string;
  outputDir: string;
  recycleDir: string;
  namingTemplate: string;
  moveInsteadOfCopy: boolean;
  overwritePolicy: "skip" | "overwrite" | "rename";
  excludePatterns: string[];
}

export interface PreviewChange {
  oldPath: string;
  newPath: string;
  action: "rename" | "move" | "skip";
  reason: string;
}

export interface PreviewResult {
  changes: PreviewChange[];
  totalChanges: number;
}

export type TaskStatus = "pending" | "running" | "completed" | "failed";
export type TaskType = "organize" | "scan" | "duplicate_scan";

export interface TaskLog {
  time: string;
  level: "info" | "warning" | "error";
  message: string;
}

export interface OrganizeTask {
  id: string;
  taskType: TaskType;
  status: TaskStatus;
  progress: number;
  currentFile?: string;
  totalFiles: number;
  processedFiles: number;
  logs: TaskLog[];
  startedAt: string;
  completedAt?: string;
}

export interface DuplicateFile {
  id: string;
  filePath: string;
  title: string;
  artist: string;
  format: string;
  bitrate: number;
  sampleRate: number;
  fileSize: number;
  modifiedAt: string;
  recommended: boolean;
}

export interface DuplicateGroup {
  id: string;
  similarity: number;
  files: DuplicateFile[];
}

export interface SystemSettings {
  musicDirs: { input: string; output: string; recycle: string };
  supportedFormats: string[];
  concurrency: number;
  logLevel: "debug" | "info" | "warning" | "error";
}

export interface Paginated<T> {
  items: T[];
  total: number;
}

// 系统日志相关类型
export interface LogEntry {
  time: string;
  level: string;
  logger: string;
  message: string;
  raw: string;
}

export interface LogListResponse {
  total: number;
  file: string;
  fileSize: number;
  entries: LogEntry[];
}
