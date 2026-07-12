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

export interface CompanionFile {
  oldPath: string;
  newPath: string;
}

export interface PreviewChange {
  oldPath: string;
  newPath: string;
  action: "rename" | "move" | "copy" | "skip";
  reason: string;
  artist?: string;
  album?: string;
  title?: string;
  trackNumber?: number;
  companions?: CompanionFile[];
}

export interface PreviewResult {
  changes: PreviewChange[];
  totalChanges: number;
  skipped: number;
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
  result?: Record<string, number | string>;
}

export interface DuplicateFile {
  songId: string;
  filePath: string;
  title: string;
  artist: string;
  format: string;
  bitrate: number;
  sampleRate: number;
  fileSize: number;
  fileModified: string;
  recommended: boolean;
}

export interface DuplicateGroup {
  id: string;
  groupHash: string;
  similarity: number;
  status: string;
  detectedAt: string;
  files: DuplicateFile[];
}

export interface SystemSettings {
  inputDir: string;
  outputDir: string;
  recycleDir: string;
  dbPath: string;
  logLevel: "debug" | "info" | "warning" | "error";
  supportedFormats: string[];
  concurrency: number;
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
