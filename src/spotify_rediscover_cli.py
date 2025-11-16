#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Spotify Rediscovery Analyzer (CLI) — TZ-safe + HTML report
----------------------------------------------------------
Adds `--html report.html` to write a beautiful, sortable HTML report
with all tables (spikes, drop-offs, dormant, one-album obsessions, top artists).
"""
import argparse, glob, json, os, sys, math, html
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

MIN_MS                = 0
SPIKE_Z               = 2.0
SPIKE_MIN_PLAYS       = 60 # was previously 8, but we wanted a higher floor
DROP_PEAK_SHARE       = 0.40
DROP_RECENT_SILENCE_M = 24
DROP_PEAK_MIN_PLAYS   = 20  # require >=20 plays in the peak month for drop-off detection (previously 10)
GRIP_MIN_HOURS        = 3.0
GRIP_DORMANT_YEARS    = 2 # was previously 3
ALBUM_DOMINANCE       = 0.80
ALBUM_MIN_MONTH_PLAYS = 20 # was previously 10
ALBUM_CONCENTRATION   = 0.70
TOP_N                 = 100

def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Spotify Rediscovery Analyzer")
    ap.add_argument("path", help="Directory or glob for StreamingHistory*.json")
    ap.add_argument("--min-ms", type=int, default=MIN_MS, help="Minimum ms_played to include (default 0)")
    ap.add_argument("--exclude-podcasts", action="store_true", help="Exclude podcast rows")
    ap.add_argument("--top", type=int, default=10, help="Top N for the all-time list (default 10)")
    ap.add_argument("--html", type=str, default=None, help="Write a full HTML report to this path")
    return ap.parse_args(argv)

def expand_files(path):
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.json")))
    else:
        return sorted(glob.glob(path))

def parse_ts(ts):
    if not ts: 
        return None
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z","+00:00")
        dt = datetime.fromisoformat(ts)
        # Ensure timezone-aware (UTC) if input lacked tzinfo
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def is_podcast(row):
    return bool(row.get("episode_name") or row.get("episode_show_name"))

def safe_meta(row):
    track = row.get("master_metadata_track_name") or ""
    album = row.get("master_metadata_album_album_name") or ""
    artist = row.get("master_metadata_album_artist_name") or ""
    return track, album, artist

def month_key(dt):
    # Always format in UTC to keep month bins stable
    return dt.astimezone(timezone.utc).strftime("%Y-%m")

def load_rows(files):
    rows = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    rows.extend(data)
        except Exception as e:
            sys.stderr.write(f"[WARN] failed to read {f}: {e}\n")
    return rows

def print_h(title):
    line = "="*80
    print("\n"+line)
    print(title)
    print(line)

def print_sub(title):
    print(f"\n— {title} —")

def hours(ms):
    return ms/1000/60/60.0

def build_html(title, params, sections):
    # sections: list of tuples (section_title, section_subtitle, table_headers, rows)
    # rows: list of iterables of columns (already formatted strings)
    css = '''
    :root{--bg:#0b0f14;--panel:#121821;--ink:#e8eef6;--muted:#9bb0c9;--accent:#7bdff6;--accent2:#b088f9;--good:#9ae6b4;--warn:#f6ad55;--bad:#feb2b2;}
    *{box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Helvetica,Arial,sans-serif}
    body{margin:0;background:linear-gradient(180deg,#0b0f14,#0d121a);color:var(--ink)}
    header{padding:28px 24px;border-bottom:1px solid #233047;background:radial-gradient(1200px 400px at 10% -10%,#11213544,transparent)}
    h1{margin:0;font-size:28px;letter-spacing:.3px}
    .meta{color:var(--muted);margin-top:6px;font-size:14px}
    .wrap{max-width:1100px;margin:0 auto;padding:22px}
    section{background:var(--panel);border:1px solid #233047;border-radius:16px;margin:18px 0;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.25)}
    section header{display:flex;justify-content:space-between;align-items:baseline;padding:16px 18px;background:linear-gradient(180deg,#121b27,#0f1621);border-bottom:1px solid #233047}
    section h2{margin:0;font-size:18px}
    section p.sub{margin:0;color:var(--muted);font-size:13px}
    .table{width:100%;border-collapse:separate;border-spacing:0}
    .table th,.table td{padding:10px 12px;border-bottom:1px solid #1f2a3a}
    .table th{position:sticky;top:0;background:#0f1621;z-index:1;text-align:left;font-weight:600;color:#c6d4ea}
    .table tr:nth-child(2n){background:#0f1520}
    .table tr:hover{background:#172033}
    .badge{display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid #2a3a53;background:#0f1621;color:#c6d4ea;font-size:12px}
    footer{color:var(--muted);padding:24px;text-align:center}
    .small{font-size:12px;color:var(--muted)}
    .mono{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace}
    .right{text-align:right}
    .nowrap{white-space:nowrap}
    .pill{padding:2px 8px;border-radius:999px}
    .ok{background:rgba(154,230,180,.12);border:1px solid rgba(154,230,180,.3)}
    .warn{background:rgba(246,173,85,.12);border:1px solid rgba(246,173,85,.3)}
    .bad{background:rgba(254,178,178,.12);border:1px solid rgba(254,178,178,.3)}
    '''
    js = '''
    // Simple table sort (click a header)
    document.querySelectorAll('table').forEach(t => {
      const ths = t.querySelectorAll('th');
      ths.forEach((th, idx) => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
          const rows = Array.from(t.querySelectorAll('tbody tr'));
          const asc = th.dataset.sortAsc === 'true' ? false : true;
          th.dataset.sortAsc = asc;
          rows.sort((a,b) => {
            let A = a.children[idx].innerText.trim();
            let B = b.children[idx].innerText.trim();
            const nA = parseFloat(A.replace(/[^0-9.-]/g,''));
            const nB = parseFloat(B.replace(/[^0-9.-]/g,''));
            if (!Number.isNaN(nA) && !Number.isNaN(nB)) { return asc ? nA - nB : nB - nA; }
            return asc ? A.localeCompare(B) : B.localeCompare(A);
          });
          rows.forEach(r => t.querySelector('tbody').appendChild(r));
        });
      });
    });
    '''
    def table_html(headers, rows):
        thead = ''.join(f'<th>{html.escape(h)}</th>' for h in headers)
        body_rows = []
        for r in rows:
            tds = ''.join(f'<td class="nowrap">{html.escape(str(c))}</td>' for c in r)
            body_rows.append(f'<tr>{tds}</tr>')
        return f'<table class="table"><thead><tr>{thead}</tr></thead><tbody>' + ''.join(body_rows) + '</tbody></table>'

    sections_html = []
    for stitle, ssub, headers, rows in sections:
        sections_html.append(f'''
            <section>
              <header>
                <div>
                  <h2>{html.escape(stitle)}</h2>
                  <p class="sub">{html.escape(ssub)}</p>
                </div>
              </header>
              <div class="wrap">
                {table_html(headers, rows) if rows else '<p class="small">No data matched this section with current thresholds.</p>'}
              </div>
            </section>
        ''')
    params_kv = ' · '.join([f'<span class="badge">{html.escape(k)}: {html.escape(str(v))}</span>' for k,v in params.items()])
    return f'''
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>{html.escape(title)}</title>
        <style>{css}</style>
      </head>
      <body>
        <header>
          <div class="wrap">
            <h1>{html.escape(title)}</h1>
            <div class="meta">{params_kv}</div>
          </div>
        </header>
        <div class="wrap">
          {''.join(sections_html)}
        </div>
        <footer>Generated {html.escape(datetime.now().isoformat(timespec="seconds"))}</footer>
        <script>{js}</script>
      </body>
    </html>
    '''

def main(argv=None):
    args = parse_args(argv)
    files = expand_files(args.path)
    if not files:
        sys.stderr.write("No JSON files found.\n")
        sys.exit(2)

    rows = load_rows(files)
    music = []
    for r in rows:
        if args.exclude_podcasts and is_podcast(r):
            continue
        ms = int(r.get("ms_played") or 0)
        if ms < args.min_ms:
            continue
        track, album, artist = safe_meta(r)
        ts = parse_ts(r.get("ts"))
        if not ts:
            continue
        music.append({"ts": ts, "ms": ms, "track": track, "album": album, "artist": artist})

    if not music:
        print("No qualifying music rows after filters.")
        sys.exit(0)

    total_ms = sum(m["ms"] for m in music)
    artists_count = Counter(m["artist"] for m in music if m["artist"])

    # Console: keep short
    print_h("Top artists (all time) — by plays")
    for i, (artist, plays) in enumerate(artists_count.most_common(args.top), start=1):
        print(f"{i:>2}. {artist}  ({plays} plays)")
    print("\n(Full results saved to HTML if --html was provided.)")

    artist_month_counts = defaultdict(Counter)  # artist -> month -> plays
    album_month_counts  = defaultdict(Counter)  # (artist, album) -> month -> plays
    artist_last_play    = {}
    album_last_play     = {}
    artist_first_play   = {}
    artist_month_total_counts = defaultdict(Counter)

    for m in music:
        mk = month_key(m["ts"])
        a  = m["artist"] or "<unknown>"
        al = m["album"] or "<unknown>"
        artist_month_counts[a][mk] += 1
        album_month_counts[(a,al)][mk] += 1
        artist_month_total_counts[a][mk] += 1

        zero_dt = datetime.min.replace(tzinfo=timezone.utc)
        artist_last_play[a] = max(artist_last_play.get(a, zero_dt), m["ts"])
        album_last_play[(a,al)] = max(album_last_play.get((a,al), zero_dt), m["ts"])

        artist_first_play[a] = min(artist_first_play.get(a, datetime.max.replace(tzinfo=timezone.utc)), m["ts"])

    all_months = sorted({month_key(m['ts']) for m in music})

    def zscore_series(counter):
        vals = [counter[m] for m in all_months]
        if not vals: return {}
        mu = sum(vals)/len(vals)
        var = sum((v-mu)**2 for v in vals)/len(vals) if len(vals)>1 else 0.0
        sd = math.sqrt(var)
        return {m: (counter[m], 0.0 if sd == 0 else (counter[m]-mu)/sd) for m in all_months}

    spikes_artist = []
    for artist, monthly in artist_month_counts.items():
        for m,(v,z) in zscore_series(monthly).items():
            if v >= SPIKE_MIN_PLAYS and z >= SPIKE_Z:
                spikes_artist.append((m, artist, v, round(z,2)))
    spikes_artist.sort(key=lambda x:(x[0], -x[2]))

    spikes_album = []
    for key, monthly in album_month_counts.items():
        for m,(v,z) in zscore_series(monthly).items():
            if v >= max(5, SPIKE_MIN_PLAYS//2) and z >= SPIKE_Z:
                artist, album = key
                spikes_album.append((m, artist, album, v, round(z,2)))
    spikes_album.sort(key=lambda x:(x[0], -x[3]))

    def months_since(dt):
        now = datetime.now(timezone.utc)
        return (now.year - dt.year) * 12 + (now.month - dt.month)

    def qualifies_dropoff(counter, last_play_dt):
        lifetime = sum(counter.values())
        if lifetime == 0: return None
        peak_m, peak_v = max(counter.items(), key=lambda kv: kv[1])
        if peak_v < DROP_PEAK_MIN_PLAYS:
            return None
        if peak_v < DROP_PEAK_SHARE * lifetime:
            return None
        if last_play_dt and months_since(last_play_dt) >= DROP_RECENT_SILENCE_M:
            return (peak_m, peak_v, lifetime)
        return None

    drop_artists = []
    for artist, monthly in artist_month_counts.items():
        res = qualifies_dropoff(monthly, artist_last_play.get(artist))
        if res:
            peak_m, peak_v, lifetime = res
            share = peak_v / lifetime
            drop_artists.append((artist, peak_m, peak_v, lifetime, round(share,2)))
    drop_artists.sort(key=lambda x:(x[1], -x[4]))

    drop_albums = []
    for key, monthly in album_month_counts.items():
        res = qualifies_dropoff(monthly, album_last_play.get(key))
        if res:
            peak_m, peak_v, lifetime = res
            a,al = key
            share = peak_v / lifetime
            drop_albums.append((a, al, peak_m, peak_v, lifetime, round(share,2)))
    drop_albums.sort(key=lambda x:(x[2], -x[5]))

    # Once-had-a-grip, now dormant
    artist_total_ms = defaultdict(int)
    for m in music:
        if m["artist"]:
            artist_total_ms[m["artist"]] += m["ms"]
    now = datetime.now(timezone.utc)
    grip_artists = []
    for a, ms_sum in artist_total_ms.items():
        last_dt = artist_last_play.get(a, datetime.min.replace(tzinfo=timezone.utc))
        dormant_years = (now - last_dt).days / 365.25 if last_dt else 100.0
        if (ms_sum/1000/60/60) >= GRIP_MIN_HOURS and dormant_years >= GRIP_DORMANT_YEARS:
            grip_artists.append((a, round(ms_sum/1000/60/60,2), round(dormant_years,1), last_dt.date().isoformat()))
    grip_artists.sort(key=lambda x:(-x[2], -x[1], x[0]))

    # One-album obsessions
    album_datetimes = defaultdict(list)
    for m in music:
        a = m["artist"] or "<unknown>"
        al = m["album"] or "<unknown>"
        album_datetimes[(a,al)].append(m["ts"])

    one_album = []
    for a, month_counts in artist_month_total_counts.items():
        for mk, artist_month_total in month_counts.items():
            if artist_month_total < ALBUM_MIN_MONTH_PLAYS:
                continue
            dominant_album = None
            dominant_plays = 0
            for (aa,al), counts in album_month_counts.items():
                if aa != a: 
                    continue
                p = counts.get(mk, 0)
                if p > dominant_plays:
                    dominant_plays = p
                    dominant_album = al
            if dominant_album and dominant_plays / artist_month_total >= ALBUM_DOMINANCE:
                times = sorted(album_datetimes[(a,dominant_album)])
                i=0; best=0
                for j in range(len(times)):
                    while times[j] - times[i] > timedelta(days=60):
                        i += 1
                    best = max(best, j-i+1)
                life = sum(album_month_counts[(a,dominant_album)].values())
                if life > 0 and best / life >= ALBUM_CONCENTRATION:
                    one_album.append((mk, a, dominant_album, dominant_plays, artist_month_total, life, round(best/life,2)))
    seen=set(); filtered=[]
    for row in sorted(one_album, key=lambda x:(x[0])):
        key=(row[1],row[2])
        if key in seen: 
            continue
        seen.add(key); filtered.append(row)

    # Build HTML if requested
    if args.html:
        title = "Spotify Rediscovery Report"
        params = {
            "Files": str(len(files)),
            "Min ms": str(args.min_ms),
            "Exclude podcasts": str(args.exclude_podcasts),
            "Top artists shown in console": str(args.top),
            "Spike z": str(SPIKE_Z),
            "Spike min plays": str(SPIKE_MIN_PLAYS),
            "Drop peak share": f"{int(DROP_PEAK_SHARE*100)}%",
            "Drop recent silence": f"{DROP_RECENT_SILENCE_M} mo",
            "Drop peak min plays": f"{DROP_PEAK_MIN_PLAYS}",
            "Grip min hours": f"{GRIP_MIN_HOURS}h",
            "Grip dormant years": f"{GRIP_DORMANT_YEARS}y",
            "Album dominance": f"{int(ALBUM_DOMINANCE*100)}%",
        }
        sections = []

        # Top artists (all-time) — capped for HTML
        top_all_raw = artists_count.most_common()
        top_all_capped = top_all_raw[0:TOP_N]   # << cap here
        top_all = [(i+1, a, plays) for i, (a, plays) in enumerate(top_all_capped)]

        sections.append(("Top artists — all time (by plays, capped at {TOP_N})",
                 "Your lifetime listening, descending by play count.",
                 ["#", "Artist", "Plays"],
                 top_all))  

        # Spikes
        sections.append(("Highest‑intensity single‑month spikes — Artist",
                         "Detected via monthly play-count z-scores; unusually high, short-lived peaks.",
                         ["Month", "Artist", "Plays", "z"],
                         [(m,a,v,z) for (m,a,v,z) in spikes_artist]))
        sections.append(("Highest‑intensity single‑month spikes — Album",
                         "Detected via monthly play-count z-scores; unusually high, short-lived peaks.",
                         ["Month", "Artist", "Album", "Plays", "z"],
                         [(m,a,al,v,z) for (m,a,al,v,z) in spikes_album]))

        # Drop-offs
        sections.append(("Massive peak → total drop‑off — Artists",
                         f"Peak month ≥ {int(DROP_PEAK_SHARE*100)}% of lifetime plays, peak month ≥ {DROP_PEAK_MIN_PLAYS} plays, and no plays in the last {DROP_RECENT_SILENCE_M} months.",
                         ["Peak Month", "Artist", "Peak Plays", "Lifetime Plays", "Peak Share %"],
                         [(pm,a,pv,life,int(100*pv/life)) for (a,pm,pv,life,share) in drop_artists]))
        sections.append(("Massive peak → total drop‑off — Albums",
                         f"Peak month ≥ {int(DROP_PEAK_SHARE*100)}% of lifetime plays, peak month ≥ {DROP_PEAK_MIN_PLAYS} plays, and no plays in the last {DROP_RECENT_SILENCE_M} months.",
                         ["Peak Month", "Artist", "Album", "Peak Plays", "Lifetime Plays", "Peak Share %"],
                         [(pm,a,al,pv,life,int(100*pv/life)) for (a,al,pm,pv,life,share) in drop_albums]))

        # Dormant
        sections.append(("Had a grip on you, now dormant",
                         f"Artists with ≥{GRIP_MIN_HOURS} hours lifetime and no plays in ≥{GRIP_DORMANT_YEARS} years.",
                         ["Artist", "Hours (lifetime)", "Dormant ~years", "Last Played"],
                         [(a,h,yrs,last) for (a,h,yrs,last) in grip_artists]))

        # One-album obsessions
        sections.append(("One‑album obsessions",
                         f"In a month, one album was ≥{int(ALBUM_DOMINANCE*100)}% of that artist’s plays AND ≥{int(ALBUM_CONCENTRATION*100)}% of the album’s lifetime plays fell within 60 days.",
                         ["Month", "Artist", "Album", "Month Plays (album)", "Month Plays (artist)", "Lifetime Plays (album)", "60‑day Concentration %"],
                         [(mk,a,al,dom,total,life,int(conc*100)) for (mk,a,al,dom,total,life,conc) in filtered]))

        html_doc = build_html(title, params, sections)
        outpath = args.html
        with open(outpath, "w", encoding="utf-8") as fh:
            fh.write(html_doc)
        print(f"\nWrote HTML report to: {os.path.abspath(outpath)}")

    # Footer
    print_h("Summary")
    print(f"Files read: {len(files)}; music rows: {len(music)}; total hours: {hours(total_ms):.1f}")
    print("Done.")

if __name__ == '__main__':
    main()
