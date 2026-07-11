import type {
  Album,
  Artist,
  DuplicateGroup,
  LibraryStats,
  OrganizeConfig,
  OrganizeTask,
  PreviewResult,
  Song,
  SystemSettings,
} from "@/types";

export const mockData = {
  stats: {
    totalSongs: 12847,
    totalArtists: 326,
    totalAlbums: 1892,
    totalDuplicates: 143,
    totalSize: 847_293_847_000,
    formatBreakdown: [
      { format: "FLAC", count: 6234 },
      { format: "MP3", count: 4892 },
      { format: "APE", count: 1023 },
      { format: "M4A", count: 512 },
      { format: "WAV", count: 186 },
    ],
  } as LibraryStats,

  artists: [
    { id: "a1", name: "周杰伦", albumCount: 16, songCount: 234, coverUrl: "" },
    { id: "a2", name: "林俊杰", albumCount: 12, songCount: 156, coverUrl: "" },
    { id: "a3", name: "陈奕迅", albumCount: 28, songCount: 312, coverUrl: "" },
    { id: "a4", name: "邓紫棋", albumCount: 9, songCount: 98, coverUrl: "" },
    { id: "a5", name: "五月天", albumCount: 15, songCount: 178, coverUrl: "" },
    { id: "a6", name: "Taylor Swift", albumCount: 11, songCount: 142, coverUrl: "" },
    { id: "a7", name: "Adele", albumCount: 4, songCount: 38, coverUrl: "" },
    { id: "a8", name: "李荣浩", albumCount: 8, songCount: 86, coverUrl: "" },
    { id: "a9", name: "薛之谦", albumCount: 7, songCount: 72, coverUrl: "" },
    { id: "a10", name: "毛不易", albumCount: 5, songCount: 54, coverUrl: "" },
    { id: "a11", name: "华晨宇", albumCount: 6, songCount: 68, coverUrl: "" },
    { id: "a12", name: "王菲", albumCount: 22, songCount: 198, coverUrl: "" },
  ] as Artist[],

  albums: [
    { id: "al1", artistId: "a1", title: "范特西", year: 2001, songCount: 10, coverUrl: "" },
    { id: "al2", artistId: "a1", title: "叶惠美", year: 2003, songCount: 11, coverUrl: "" },
    { id: "al3", artistId: "a1", title: "七里香", year: 2004, songCount: 10, coverUrl: "" },
    { id: "al4", artistId: "a1", title: "十一月的萧邦", year: 2005, songCount: 12, coverUrl: "" },
    { id: "al5", artistId: "a2", title: "第二天堂", year: 2004, songCount: 10, coverUrl: "" },
    { id: "al6", artistId: "a2", title: "编号89757", year: 2005, songCount: 11, coverUrl: "" },
    { id: "al7", artistId: "a3", title: "U87", year: 2005, songCount: 10, coverUrl: "" },
    { id: "al8", artistId: "a3", title: "黑白灰", year: 2003, songCount: 11, coverUrl: "" },
    { id: "al9", artistId: "a4", title: "新的心跳", year: 2015, songCount: 10, coverUrl: "" },
    { id: "al10", artistId: "a5", title: "自传", year: 2016, songCount: 12, coverUrl: "" },
    { id: "al11", artistId: "a6", title: "1989", year: 2014, songCount: 13, coverUrl: "" },
    { id: "al12", artistId: "a7", title: "25", year: 2015, songCount: 11, coverUrl: "" },
  ] as Album[],

  songs: [
    { id: "s1", albumId: "al1", title: "简单爱", trackNumber: 3, duration: 273, format: "FLAC", bitrate: 992, sampleRate: 44100, channels: 2, filePath: "/music/周杰伦/范特西/03-简单爱.flac", fileSize: 34_560_000 },
    { id: "s2", albumId: "al1", title: "爱在西元前", trackNumber: 1, duration: 285, format: "FLAC", bitrate: 992, sampleRate: 44100, channels: 2, filePath: "/music/周杰伦/范特西/01-爱在西元前.flac", fileSize: 36_120_000 },
    { id: "s3", albumId: "al1", title: "爸我回来了", trackNumber: 2, duration: 234, format: "FLAC", bitrate: 992, sampleRate: 44100, channels: 2, filePath: "/music/周杰伦/范特西/02-爸我回来了.flac", fileSize: 29_340_000 },
    { id: "s4", albumId: "al1", title: "忍者", trackNumber: 4, duration: 162, format: "FLAC", bitrate: 992, sampleRate: 44100, channels: 2, filePath: "/music/周杰伦/范特西/04-忍者.flac", fileSize: 20_160_000 },
    { id: "s5", albumId: "al1", title: "双截棍", trackNumber: 6, duration: 264, format: "FLAC", bitrate: 992, sampleRate: 44100, channels: 2, filePath: "/music/周杰伦/范特西/06-双截棍.flac", fileSize: 33_000_000 },
    { id: "s6", albumId: "al1", title: "安静", trackNumber: 10, duration: 312, format: "FLAC", bitrate: 992, sampleRate: 44100, channels: 2, filePath: "/music/周杰伦/范特西/10-安静.flac", fileSize: 39_000_000 },
  ] as Song[],

  organizeConfig: {
    inputDir: "/music",
    outputDir: "/music",
    recycleDir: "/music/.recycle",
    namingTemplate: "{artist}/{album}/{track:02d}-{title}",
    moveInsteadOfCopy: true,
    overwritePolicy: "skip" as const,
    excludePatterns: ["*.tmp", "*.bak", ".DS_Store"],
  } as OrganizeConfig,

  previewResult: {
    changes: [
      { oldPath: "/music/周杰伦 - 简单爱.flac", newPath: "/music/周杰伦/范特西/03-简单爱.flac", action: "rename" as const, reason: "按元数据规范化文件名和目录" },
      { oldPath: "/music/unknown_track.mp3", newPath: "/music/周杰伦/范特西/01-爱在西元前.mp3", action: "rename" as const, reason: "元数据补全并规范化" },
      { oldPath: "/music/双截棍.flac", newPath: "/music/周杰伦/范特西/06-双截棍.flac", action: "move" as const, reason: "移动到对应艺术家专辑目录" },
    ],
    totalChanges: 3,
  } as PreviewResult,

  task: {
    id: "task-001",
    taskType: "organize" as const,
    status: "running" as const,
    progress: 67,
    currentFile: "/music/周杰伦/范特西/06-双截棍.flac",
    totalFiles: 12847,
    processedFiles: 8607,
    logs: [
      { time: "2026-07-11 10:00:00", level: "info" as const, message: "开始扫描音乐目录 /music" },
      { time: "2026-07-11 10:00:05", level: "info" as const, message: "发现 12847 个音频文件" },
      { time: "2026-07-11 10:00:10", level: "info" as const, message: "正在处理: 周杰伦 - 简单爱.flac" },
      { time: "2026-07-11 10:00:15", level: "info" as const, message: "重命名: 周杰伦 - 简单爱.flac → 范特西/03-简单爱.flac" },
      { time: "2026-07-11 10:15:00", level: "warning" as const, message: "元数据缺失: unknown_track.mp3，尝试在线查询" },
      { time: "2026-07-11 10:15:05", level: "info" as const, message: "MusicBrainz 匹配成功: 爱在西元前" },
    ],
    startedAt: "2026-07-11T10:00:00",
  } as OrganizeTask,

  recentTasks: [
    { id: "task-001", taskType: "organize" as const, status: "running" as const, progress: 67, currentFile: "/music/周杰伦/范特西/06-双截棍.flac", totalFiles: 12847, processedFiles: 8607, logs: [], startedAt: "2026-07-11T10:00:00" },
    { id: "task-002", taskType: "duplicate_scan" as const, status: "completed" as const, progress: 100, totalFiles: 12847, processedFiles: 12847, logs: [], startedAt: "2026-07-10T15:00:00", completedAt: "2026-07-10T15:30:00" },
    { id: "task-003", taskType: "organize" as const, status: "completed" as const, progress: 100, totalFiles: 8500, processedFiles: 8500, logs: [], startedAt: "2026-07-09T09:00:00", completedAt: "2026-07-09T09:45:00" },
  ] as OrganizeTask[],

  duplicateGroups: [
    {
      id: "dg1",
      similarity: 100,
      files: [
        { id: "df1", filePath: "/music/周杰伦/范特西/03-简单爱.flac", title: "简单爱", artist: "周杰伦", format: "FLAC", bitrate: 992, sampleRate: 44100, fileSize: 34_560_000, modifiedAt: "2026-01-15", recommended: true },
        { id: "df2", filePath: "/music/下载/简单爱.mp3", title: "简单爱", artist: "周杰伦", format: "MP3", bitrate: 320, sampleRate: 44100, fileSize: 10_920_000, modifiedAt: "2025-11-20", recommended: false },
      ],
    },
    {
      id: "dg2",
      similarity: 98,
      files: [
        { id: "df3", filePath: "/music/陈奕迅/U87/浮夸.flac", title: "浮夸", artist: "陈奕迅", format: "FLAC", bitrate: 992, sampleRate: 44100, fileSize: 38_400_000, modifiedAt: "2026-02-01", recommended: true },
        { id: "df4", filePath: "/music/陈奕迅/精选/浮夸.mp3", title: "浮夸", artist: "陈奕迅", format: "MP3", bitrate: 320, sampleRate: 44100, fileSize: 11_280_000, modifiedAt: "2025-12-10", recommended: false },
        { id: "df5", filePath: "/music/backup/浮夸.ape", title: "浮夸", artist: "陈奕迅", format: "APE", bitrate: 800, sampleRate: 44100, fileSize: 30_000_000, modifiedAt: "2025-08-05", recommended: false },
      ],
    },
    {
      id: "dg3",
      similarity: 95,
      files: [
        { id: "df6", filePath: "/music/林俊杰/第二天堂/江南.flac", title: "江南", artist: "林俊杰", format: "FLAC", bitrate: 992, sampleRate: 44100, fileSize: 35_200_000, modifiedAt: "2026-03-01", recommended: true },
        { id: "df7", filePath: "/music/下载/江南.m4a", title: "江南", artist: "林俊杰", format: "M4A", bitrate: 256, sampleRate: 44100, fileSize: 8_960_000, modifiedAt: "2025-10-15", recommended: false },
      ],
    },
  ] as DuplicateGroup[],

  settings: {
    inputDir: "/music",
    outputDir: "/music",
    recycleDir: "/music/.recycle",
    dbPath: "/app/data/melodybox.db",
    logLevel: "info" as const,
    supportedFormats: ["MP3", "FLAC", "APE", "WAV", "M4A", "OGG", "OPUS"],
    concurrency: 4,
  } as SystemSettings,
};
