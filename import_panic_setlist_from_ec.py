#!/usr/bin/env python3
"""
import_setlist.py — Import a Widespread Panic setlist text file into show_data.db

Usage:
    python import_setlist.py <setlist.txt> [--db show_data.db] [--dry-run]

Text file format:
    MM/DD/YY Venue Name, City, ST
    1: Song One, Song Two > Song Three, Song Four
    2: Song Five, Song Six
    E: Encore Song

    MM/DD/YY Next Venue, City, ST
    ...

Notes:
  - Sets are labeled 1:, 2:, 3:, E:  (any label before a colon is accepted)
  - '>' denotes a segue between songs
  - '*' anywhere in a song name is silently stripped
  - Blank lines separate shows
  - If a venue or song doesn't exist in the DB it will be created
  - If a show on that date/venue already exists the script will skip it
"""

import sqlite3
import re
import sys
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_file(path: str) -> list[dict]:
    """Parse a setlist text file and return a list of show dicts."""
    shows = []
    current_show = None

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f]

    for line in lines:
        if not line.strip():
            # Blank line ends the current show
            if current_show:
                shows.append(current_show)
                current_show = None
            continue

        # Try to match a date/venue header: MM/DD/YY Venue, City, ST
        header = re.match(
            r'^(\d{2})/(\d{2})/(\d{2,4})\s+(.+)$', line
        )
        if header:
            if current_show:
                shows.append(current_show)
            month, day, year_raw, venue_str = header.groups()
            year = int(year_raw)
            if year < 100:
                year += 2000
            venue_parts = [p.strip() for p in venue_str.split(',')]
            current_show = {
                "year": year,
                "month": int(month),
                "day": int(day),
                "venue_parts": venue_parts,
                "sets": [],
            }
            continue

        # Try to match a set line: "1:", "2:", "E:", etc.
        set_match = re.match(r'^([^:]+):\s*(.+)$', line)
        if set_match and current_show is not None:
            set_label = set_match.group(1).strip()
            set_contents = set_match.group(2).strip()
            songs = parse_set_string(set_contents)
            current_show["sets"].append({
                "label": set_label,
                "songs": songs,
            })
            continue

        # Unrecognised line — warn but continue
        print(f"  [WARN] Skipping unrecognised line: {line!r}")

    # Don't forget the last show if file doesn't end with a blank line
    if current_show:
        shows.append(current_show)

    return shows


def parse_set_string(set_str: str) -> list[tuple[str, int]]:
    """
    Parse a set string into a list of (song_name, segue) tuples.
    Song names containing commas should be wrapped in double quotes.
    e.g.: "Lawyers, Guns, And Money", Other Song > Segued Song
    """
    songs = []
    # Normalize curly quotes (common when copy-pasting from the web)
    set_str = set_str.replace('\u201c', '"').replace('\u201d', '"')
    # An item is a run of quoted strings and/or non-comma characters.
    # This keeps quoted commas inside one item wherever the quotes appear,
    # including mid-string and inside segue chains.
    pattern = re.compile(r'(?:"[^"]*"|[^,"])+')
    items = [m.group().strip() for m in pattern.finditer(set_str)]

    for item in items:
        parts = [p.strip() for p in item.split(' > ')]
        for i, part in enumerate(parts):
            # Remove asterisks first, then strip quotes and whitespace
            name = part.replace('*', '').strip().strip('"').strip()
            segue = 1 if i < len(parts) - 1 else 0
            if name:
                songs.append((name, segue))
    return songs


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_or_create_venue(cur: sqlite3.Cursor, parts: list[str]) -> int:
    """
    Look up a venue by its first part (name). Create it if not found.
    venue_parts is [name, city?, state?, ...] from the text file header.
    """
    venue_name = parts[0] if len(parts) > 0 else ""
    city       = parts[1] if len(parts) > 1 else None
    state      = parts[2] if len(parts) > 2 else None

    cur.execute("SELECT id FROM venues WHERE venue1 = ?", (venue_name,))
    row = cur.fetchone()
    if row:
        return row[0]

    # Create new venue
    cur.execute(
        "INSERT INTO venues (venue1, venue2, venue3) VALUES (?, ?, ?)",
        (venue_name, city, state),
    )
    new_id = cur.lastrowid
    print(f"    [NEW VENUE] '{venue_name}', {city}, {state} (id={new_id})")
    return new_id


def get_or_create_song(cur: sqlite3.Cursor, name: str) -> int:
    """Look up a song by name. Create it if not found."""
    cur.execute("SELECT id FROM songs WHERE song = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("INSERT INTO songs (song) VALUES (?)", (name,))
    new_id = cur.lastrowid
    print(f"    [NEW SONG] '{name}' (id={new_id})")
    return new_id


def get_act_id(cur: sqlite3.Cursor, name: str = "Widespread Panic") -> int:
    cur.execute("SELECT id FROM acts WHERE name = ?", (name,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Act '{name}' not found in database.")
    return row[0]


def show_exists(cur: sqlite3.Cursor, act_id: int, venue_id: int,
                year: int, month: int, day: int) -> bool:
    cur.execute(
        "SELECT id FROM events WHERE act_id=? AND venue_id=? AND year=? AND month=? AND day=?",
        (act_id, venue_id, year, month, day),
    )
    return cur.fetchone() is not None


# ---------------------------------------------------------------------------
# Insertion
# ---------------------------------------------------------------------------

SET_ORDER = {}  # built dynamically from set label sequence


def insert_show(cur: sqlite3.Cursor, show: dict, act_id: int, dry_run: bool) -> None:
    year, month, day = show["year"], show["month"], show["day"]
    venue_id = get_or_create_venue(cur, show["venue_parts"])

    if show_exists(cur, act_id, venue_id, year, month, day):
        print(f"  [SKIP] {month:02d}/{day:02d}/{year} already in DB — skipping.")
        return

    print(f"  Inserting {month:02d}/{day:02d}/{year} @ {show['venue_parts'][0]}")

    if dry_run:
        for i, s in enumerate(show["sets"]):
            print(f"    Set {s['label']}: {len(s['songs'])} songs")
        return

    cur.execute(
        "INSERT INTO events (act_id, venue_id, year, month, day, event_no) VALUES (?,?,?,?,?,1)",
        (act_id, venue_id, year, month, day),
    )
    event_id = cur.lastrowid

    for seq, s in enumerate(show["sets"], start=1):
        cur.execute(
            'INSERT INTO event_sets (event_id, "set", seq) VALUES (?,?,?)',
            (event_id, s["label"], seq),
        )
        event_set_id = cur.lastrowid

        for position, (song_name, segue) in enumerate(s["songs"], start=1):
            song_id = get_or_create_song(cur, song_name)
            cur.execute(
                "INSERT INTO event_songs (event_set_id, song_id, seq, segue) VALUES (?,?,?,?)",
                (event_set_id, song_id, position, segue),
            )

    total_songs = sum(len(s["songs"]) for s in show["sets"])
    print(f"    -> event_id={event_id}, {len(show['sets'])} sets, {total_songs} songs")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Import a WSP setlist text file into show_data.db")
    parser.add_argument("setlist", help="Path to the setlist .txt file")
    parser.add_argument("--db", default="show_data.db", help="Path to the SQLite database (default: show_data.db)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing to the database")
    args = parser.parse_args()

    if not Path(args.setlist).exists():
        print(f"Error: file not found: {args.setlist}")
        sys.exit(1)

    if not Path(args.db).exists():
        print(f"Error: database not found: {args.db}")
        sys.exit(1)

    print(f"Parsing {args.setlist} ...")
    shows = parse_file(args.setlist)
    print(f"Found {len(shows)} show(s).\n")

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    try:
        act_id = get_act_id(cur)
        for show in shows:
            insert_show(cur, show, act_id, dry_run=args.dry_run)

        if not args.dry_run:
            conn.commit()
            print(f"\nCommitted {len(shows)} show(s) to {args.db}.")
        else:
            print("\n[DRY RUN] No changes written.")
    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()