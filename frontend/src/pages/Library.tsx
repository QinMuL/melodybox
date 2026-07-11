import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronRight, Disc3, Music2, Search } from "lucide-react";
import { api } from "@/lib/api";
import { formatDuration, formatSize, formatBitrate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Album, Artist, Song } from "@/types";

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

  useEffect(() => {
    api.library.artists(1, 100).then((res) => {
      setArtists(res.items);
      setLoading(false);
    });
  }, []);

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

  const handleBack = () => {
    if (view === "songs") {
      setView("albums");
      setSelectedAlbum(null);
    } else if (view === "albums") {
      setView("artists");
      setSelectedArtist(null);
    }
  };

  if (query) {
    return <SearchView query={query} />;
  }

  return (
    <div className="space-y-5">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm">
        <button
          onClick={() => {
            setView("artists");
            setSelectedArtist(null);
            setSelectedAlbum(null);
          }}
          className={cn(
            "transition-colors",
            view === "artists"
              ? "font-semibold text-primary"
              : "text-ink-muted hover:text-primary dark:text-ink-lightMuted"
          )}
        >
          艺术家
        </button>
        {selectedArtist && (
          <>
            <ChevronRight className="h-4 w-4 text-ink-muted" />
            <button
              onClick={handleBack}
              className={cn(
                "transition-colors",
                view === "albums"
                  ? "font-semibold text-primary"
                  : "text-ink-muted hover:text-primary dark:text-ink-lightMuted"
              )}
            >
              {selectedArtist.name}
            </button>
          </>
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
          <div className="mx-auto mb-3 flex h-20 w-20 items-center justify-center rounded-full bg-primary-gradient text-2xl font-bold text-white shadow-primary transition-transform group-hover:scale-105">
            {artist.name.charAt(0)}
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
            <div className="flex h-full items-center justify-center text-4xl font-bold text-white/30">
              <Disc3 className="h-12 w-12" />
            </div>
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
        <p>{albumTitle} 暂无歌曲数据</p>
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
          {songs.map((song) => (
            <tr
              key={song.id}
              className="group border-b border-surface-border transition-colors hover:bg-surface-hover dark:border-dark-border/50 dark:hover:bg-dark-hover"
            >
              <td className="px-4 py-3 font-mono text-sm text-ink-muted dark:text-ink-lightMuted">
                {String(song.trackNumber).padStart(2, "0")}
              </td>
              <td className="px-4 py-3">
                <span className="text-sm font-medium text-ink-primary dark:text-ink-light">
                  {song.title}
                </span>
              </td>
              <td className="hidden px-4 py-3 md:table-cell">
                <span className="rounded bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary dark:bg-primary-900/20 dark:text-primary-300">
                  {song.format}
                </span>
              </td>
              <td className="hidden px-4 py-3 font-mono text-xs text-ink-secondary dark:text-ink-lightSecondary lg:table-cell">
                {formatBitrate(song.bitrate)}
              </td>
              <td className="hidden px-4 py-3 font-mono text-xs text-ink-secondary dark:text-ink-lightSecondary lg:table-cell">
                {formatSize(song.fileSize)}
              </td>
              <td className="px-4 py-3 text-right font-mono text-sm text-ink-secondary dark:text-ink-lightSecondary">
                {formatDuration(song.duration)}
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
