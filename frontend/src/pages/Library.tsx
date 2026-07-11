import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronRight, Disc3, Music2, Search } from "lucide-react";
import { api } from "@/lib/api";
import { formatDuration, formatSize, formatBitrate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Album, Artist, Song } from "@/types";

/** 带回退的图片组件：加载失败时显示 children */
function ImageWithFallback({
  src,
  alt,
  className,
  children,
}: {
  src: string;
  alt: string;
  className?: string;
  children: React.ReactNode;
}) {
  const [failed, setFailed] = useState(false);
  if (failed) return <>{children}</>;
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      className={className}
    />
  );
}

type View = "artists" | "albums" | "songs";

export default function Library() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";

  const [view, setView] = useState<View>("artists");
  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [albums, setAlbums] = useState<Album[]>([]);
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);

  // 加载艺术家列表
  useEffect(() => {
    setLoading(true);
    api.library.artists(1, 100).then((res) => {
      setArtists(res.items);
      setLoading(false);
    });
  }, []);

  // 切换到专辑视图时加载全部专辑
  useEffect(() => {
    if (view === "albums" && !selectedArtist) {
      setLoading(true);
      api.library.allAlbums(1, 100).then((res) => {
        setAlbums(res.items);
        setLoading(false);
      });
    }
  }, [view, selectedArtist]);

  // 切换到歌曲视图时加载全部歌曲
  useEffect(() => {
    if (view === "songs" && !selectedAlbum) {
      setLoading(true);
      api.library.allSongs(1, 200).then((res) => {
        setSongs(res.items);
        setLoading(false);
      });
    }
  }, [view, selectedAlbum]);

  const handleArtistClick = async (artist: Artist) => {
    setSelectedArtist(artist);
    setView("albums");
    setLoading(true);
    const res = await api.library.albums(artist.id);
    setAlbums(res.items);
    setLoading(false);
  };

  const handleAlbumClick = async (album: Album) => {
    setSelectedAlbum(album);
    setView("songs");
    setLoading(true);
    const res = await api.library.songs(album.id);
    setSongs(res.items);
    setLoading(false);
  };

  const handleTabChange = (tab: View) => {
    setView(tab);
    setSelectedArtist(null);
    setSelectedAlbum(null);
  };

  const handleBack = () => {
    if (view === "songs" && selectedAlbum) {
      // 从专辑歌曲返回到专辑列表
      setView("albums");
      setSelectedAlbum(null);
    } else if (view === "albums" && selectedArtist) {
      // 从艺术家专辑返回到艺术家列表
      setView("artists");
      setSelectedArtist(null);
    }
  };

  if (query) {
    return <SearchView query={query} />;
  }

  return (
    <div className="space-y-5">
      {/* 视图切换标签 */}
      <div className="flex items-center gap-1 border-b border-surface-border dark:border-dark-border">
        {(["artists", "albums", "songs"] as View[]).map((tab) => (
          <button
            key={tab}
            onClick={() => handleTabChange(tab)}
            className={cn(
              "relative px-4 py-2.5 text-sm font-medium transition-colors",
              view === tab
                ? "text-primary"
                : "text-ink-muted hover:text-ink-primary dark:text-ink-lightMuted dark:hover:text-ink-light"
            )}
          >
            {tab === "artists" ? "艺术家" : tab === "albums" ? "专辑" : "歌曲"}
            {view === tab && (
              <span className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-primary" />
            )}
          </button>
        ))}
      </div>

      {/* 面包屑（层级浏览时显示） */}
      {(selectedArtist || selectedAlbum) && (
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={handleBack}
            className="text-ink-muted transition-colors hover:text-primary dark:text-ink-lightMuted"
          >
            ← 返回
          </button>
          <ChevronRight className="h-4 w-4 text-ink-muted" />
          {selectedArtist && (
            <span className="font-semibold text-primary">
              {selectedArtist.name}
            </span>
          )}
          {selectedAlbum && (
            <>
              <ChevronRight className="h-4 w-4 text-ink-muted" />
              <span className="font-semibold text-primary">
                {selectedAlbum.title}
              </span>
            </>
          )}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="h-48 animate-pulse rounded-xl bg-surface-card dark:bg-dark-card"
            />
          ))}
        </div>
      ) : view === "artists" ? (
        <ArtistGrid artists={artists} onClick={handleArtistClick} />
      ) : view === "albums" ? (
        <AlbumGrid
          albums={albums}
          artistName={selectedArtist?.name}
          onClick={handleAlbumClick}
        />
      ) : (
        <SongList songs={songs} albumTitle={selectedAlbum?.title} />
      )}
    </div>
  );
}

function ArtistGrid({
  artists,
  onClick,
}: {
  artists: Artist[];
  onClick: (artist: Artist) => void;
}) {
  if (artists.length === 0) {
    return (
      <div className="py-20 text-center text-ink-muted dark:text-ink-lightMuted">
        <Music2 className="mx-auto mb-3 h-12 w-12 opacity-30" />
        <p>音乐库为空，请先扫描音乐目录</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
      {artists.map((artist, idx) => (
        <button
          key={artist.id}
          onClick={() => onClick(artist)}
          className="card group p-4 text-center hover:-translate-y-1 hover:shadow-cardHover"
          style={{ animationDelay: `${idx * 40}ms` }}
        >
          <div className="mx-auto mb-3 h-20 w-20 overflow-hidden rounded-full bg-primary-gradient shadow-primary transition-transform group-hover:scale-105">
            <ImageWithFallback
              src={`/api/library/artists/${artist.id}/avatar`}
              alt={artist.name}
              className="h-full w-full object-cover"
            >
              <div className="flex h-full w-full items-center justify-center text-2xl font-bold text-white">
                {artist.name.charAt(0)}
              </div>
            </ImageWithFallback>
          </div>
          <h4 className="truncate text-sm font-medium text-ink-primary dark:text-ink-light">
            {artist.name}
          </h4>
          <p className="mt-1 text-xs text-ink-muted dark:text-ink-lightMuted">
            {artist.albumCount} 张专辑 · {artist.songCount} 首
          </p>
        </button>
      ))}
    </div>
  );
}

function AlbumGrid({
  albums,
  artistName,
  onClick,
}: {
  albums: Album[];
  artistName?: string;
  onClick: (album: Album) => void;
}) {
  if (albums.length === 0) {
    return (
      <div className="py-20 text-center text-ink-muted dark:text-ink-lightMuted">
        <Disc3 className="mx-auto mb-3 h-12 w-12 opacity-30" />
        <p>{artistName ? `${artistName} 暂无专辑数据` : "暂无专辑数据"}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
      {albums.map((album, idx) => (
        <button
          key={album.id}
          onClick={() => onClick(album)}
          className="card group text-left hover:-translate-y-1 hover:shadow-cardHover"
          style={{ animationDelay: `${idx * 40}ms` }}
        >
          <div className="relative aspect-square overflow-hidden rounded-t-xl bg-gradient-to-br from-primary-400 to-primary-700">
            <ImageWithFallback
              src={`/api/library/albums/${album.id}/cover`}
              alt={album.title}
              className="h-full w-full object-cover"
            >
              <div className="flex h-full items-center justify-center text-4xl font-bold text-white/30">
                <Disc3 className="h-12 w-12" />
              </div>
            </ImageWithFallback>
            <div className="absolute inset-0 bg-black/0 transition-colors group-hover:bg-black/20" />
          </div>
          <div className="p-3">
            <h4 className="truncate text-sm font-medium text-ink-primary dark:text-ink-light">
              {album.title}
            </h4>
            <p className="mt-0.5 text-xs text-ink-muted dark:text-ink-lightMuted">
              {album.year ? `${album.year} · ` : ""}{album.songCount} 首
            </p>
          </div>
        </button>
      ))}
    </div>
  );
}

function SongList({ songs, albumTitle }: { songs: Song[]; albumTitle?: string }) {
  if (songs.length === 0) {
    return (
      <div className="py-20 text-center text-ink-muted dark:text-ink-lightMuted">
        <Music2 className="mx-auto mb-3 h-12 w-12 opacity-30" />
        <p>{albumTitle ? `${albumTitle} 暂无歌曲数据` : "暂无歌曲数据"}</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-surface-border bg-surface-hover text-left text-xs text-ink-muted dark:border-dark-border dark:bg-dark-hover dark:text-ink-lightMuted">
            <th className="w-12 px-4 py-3 font-medium">#</th>
            <th className="px-4 py-3 font-medium">标题</th>
            <th className="hidden px-4 py-3 font-medium md:table-cell">格式</th>
            <th className="hidden px-4 py-3 font-medium lg:table-cell">码率</th>
            <th className="hidden px-4 py-3 font-medium lg:table-cell">大小</th>
            <th className="px-4 py-3 text-right font-medium">时长</th>
          </tr>
        </thead>
        <tbody>
          {songs.map((song, idx) => (
            <tr
              key={song.id}
              className="group border-b border-surface-border transition-colors hover:bg-surface-hover dark:border-dark-border/50 dark:hover:bg-dark-hover"
            >
              <td className="px-4 py-3 font-mono text-sm text-ink-muted dark:text-ink-lightMuted">
                {song.trackNumber != null
                  ? String(song.trackNumber).padStart(2, "0")
                  : idx + 1}
              </td>
              <td className="px-4 py-3">
                <span className="text-sm font-medium text-ink-primary dark:text-ink-light">
                  {song.title}
                </span>
              </td>
              <td className="hidden px-4 py-3 md:table-cell">
                {song.format && (
                  <span className="rounded bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary dark:bg-primary-900/20 dark:text-primary-300">
                    {song.format}
                  </span>
                )}
              </td>
              <td className="hidden px-4 py-3 font-mono text-xs text-ink-secondary dark:text-ink-lightSecondary lg:table-cell">
                {song.bitrate ? formatBitrate(song.bitrate) : "-"}
              </td>
              <td className="hidden px-4 py-3 font-mono text-xs text-ink-secondary dark:text-ink-lightSecondary lg:table-cell">
                {song.fileSize ? formatSize(song.fileSize) : "-"}
              </td>
              <td className="px-4 py-3 text-right font-mono text-sm text-ink-secondary dark:text-ink-lightSecondary">
                {song.duration ? formatDuration(song.duration) : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SearchView({ query }: { query: string }) {
  const [results, setResults] = useState<{
    songs: Song[];
    artists: Artist[];
    albums: Album[];
  }>({ songs: [], artists: [], albums: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.library.search(query).then((res) => {
      setResults(res);
      setLoading(false);
    });
  }, [query]);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <Search className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-semibold text-ink-primary dark:text-ink-light">
          搜索结果："{query}"
        </h2>
      </div>
      {loading ? (
        <div className="h-40 animate-pulse rounded-xl bg-surface-card dark:bg-dark-card" />
      ) : results.artists.length === 0 &&
        results.albums.length === 0 &&
        results.songs.length === 0 ? (
        <div className="py-20 text-center text-ink-muted dark:text-ink-lightMuted">
          <Search className="mx-auto mb-3 h-12 w-12 opacity-30" />
          <p>未找到匹配结果</p>
        </div>
      ) : (
        <div className="space-y-6">
          {results.artists.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-ink-secondary dark:text-ink-lightSecondary">
                艺术家 ({results.artists.length})
              </h3>
              <ArtistGrid artists={results.artists} onClick={() => {}} />
            </div>
          )}
          {results.songs.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-ink-secondary dark:text-ink-lightSecondary">
                歌曲 ({results.songs.length})
              </h3>
              <SongList songs={results.songs} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
