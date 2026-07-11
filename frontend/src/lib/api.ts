import axios from "axios";
import type {
  Album,
  Artist,
  DuplicateGroup,
  LibraryStats,
  LogListResponse,
  OrganizeConfig,
  OrganizeTask,
  Paginated,
  PreviewResult,
  Song,
  SystemSettings,
} from "@/types";
import { mockData } from "./mock";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

// 请求失败时回退到 mock 数据
async function withFallback<T>(request: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await request();
  } catch (err) {
    if (import.meta.env.DEV) {
      console.warn("API 请求失败，使用 mock 数据:", err);
      return fallback;
    }
    throw err;
  }
}

export const api = {
  // 音乐库
  library: {
    stats: () =>
      withFallback(
        () => client.get<LibraryStats>("/library/stats").then((r) => r.data),
        mockData.stats
      ),
    artists: (page = 1, pageSize = 50) =>
      withFallback(
        () =>
          client
            .get<Paginated<Artist>>("/library/artists", { params: { page, pageSize } })
            .then((r) => r.data),
        { items: mockData.artists, total: mockData.artists.length }
      ),
    albums: (artistId: string) =>
      withFallback(
        () =>
          client
            .get<{ items: Album[] }>(`/library/artists/${artistId}/albums`)
            .then((r) => r.data),
        { items: mockData.albums.filter((a) => a.artistId === artistId) }
      ),
    songs: (albumId: string) =>
      withFallback(
        () =>
          client
            .get<{ items: Song[] }>(`/library/albums/${albumId}/songs`)
            .then((r) => r.data),
        { items: mockData.songs.filter((s) => s.albumId === albumId) }
      ),
    allSongs: (page = 1, pageSize = 100) =>
      withFallback(
        () =>
          client
            .get<Paginated<Song>>("/library/songs", { params: { page, pageSize } })
            .then((r) => r.data),
        { items: mockData.songs, total: mockData.songs.length }
      ),
    allAlbums: (page = 1, pageSize = 50) =>
      withFallback(
        () =>
          client
            .get<Paginated<Album>>("/library/albums", { params: { page, pageSize } })
            .then((r) => r.data),
        { items: mockData.albums, total: mockData.albums.length }
      ),
    search: (q: string) =>
      withFallback(
        () =>
          client
            .get<{ songs: Song[]; artists: Artist[]; albums: Album[] }>(
              "/library/search",
              { params: { q } }
            )
            .then((r) => r.data),
        { songs: [], artists: [], albums: [] }
      ),
    scan: (directory?: string) =>
      withFallback(
        () =>
          client
            .post<{ taskId: string; status: string }>("/library/scan", {
              directory,
              computeHash: false,
            })
            .then((r) => r.data),
        { taskId: "mock-scan-001", status: "pending" }
      ),
    scanStatus: () =>
      withFallback(
        () => client.get("/library/scan/status").then((r) => r.data),
        null
      ),
  },

  // 整理
  organize: {
    config: () =>
      withFallback(
        () => client.get<OrganizeConfig>("/organize/config").then((r) => r.data),
        mockData.organizeConfig
      ),
    updateConfig: (config: OrganizeConfig) =>
      client.put("/organize/config", config).then((r) => r.data),
    preview: () =>
      withFallback(
        () =>
          client.post<PreviewResult>("/organize/preview", { dryRun: true }).then((r) => r.data),
        mockData.previewResult
      ),
    start: (dryRun = false) =>
      withFallback(
        () => client.post<{ taskId: string }>("/organize/start", { dryRun }).then((r) => r.data),
        { taskId: "mock-task-001" }
      ),
    task: (taskId: string) =>
      withFallback(
        () => client.get<OrganizeTask>(`/organize/tasks/${taskId}`).then((r) => r.data),
        mockData.task
      ),
    tasks: (page = 1, pageSize = 10) =>
      withFallback(
        () =>
          client
            .get<Paginated<OrganizeTask>>("/organize/tasks", { params: { page, pageSize } })
            .then((r) => r.data),
        { items: mockData.recentTasks, total: mockData.recentTasks.length }
      ),
  },

  // 去重
  duplicates: {
    scan: () =>
      withFallback(
        () => client.post<{ taskId: string }>("/duplicates/scan").then((r) => r.data),
        { taskId: "mock-dup-scan-001" }
      ),
    groups: (page = 1, pageSize = 20) =>
      withFallback(
        () =>
          client
            .get<Paginated<DuplicateGroup>>("/duplicates/groups", { params: { page, pageSize } })
            .then((r) => r.data),
        { items: mockData.duplicateGroups, total: mockData.duplicateGroups.length }
      ),
    resolve: (groupId: string, keepFileId: string, action: "recycle" | "delete") =>
      client
        .post(`/duplicates/groups/${groupId}/resolve`, { keepFileId, action })
        .then((r) => r.data),
  },

  // 设置
  settings: {
    get: () =>
      withFallback(
        () => client.get<SystemSettings>("/settings/").then((r) => r.data),
        mockData.settings
      ),
    update: (settings: SystemSettings) =>
      client.put("/settings/", settings).then((r) => r.data),
    testDir: (path: string) =>
      withFallback(
        () =>
          client
            .post<{
              accessible: boolean;
              writable: boolean;
              message: string;
              fileCount: number;
            }>("/settings/test-dir", { path })
            .then((r) => r.data),
        { accessible: false, writable: false, message: "开发模式：无法访问目录", fileCount: 0 }
      ),
  },

  // 系统日志
  logs: {
    list: (params: { level?: string; search?: string; limit?: number }) =>
      withFallback(
        () =>
          client
            .get<LogListResponse>("/logs/", { params })
            .then((r) => r.data),
        {
          total: 0,
          file: "/app/data/logs/melodybox.log",
          fileSize: 0,
          entries: [],
        }
      ),
    files: () =>
      withFallback(
        () => client.get<string[]>("/logs/files").then((r) => r.data),
        ["melodybox.log"]
      ),
    clear: () => client.delete("/logs/").then((r) => r.data),
  },
};
