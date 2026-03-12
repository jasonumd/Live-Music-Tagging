#!/usr/bin/env python3
"""
Audio Metadata Updater for Concert Recordings

Reads concert dates from folder names, queries a SQLite database for show information,
and updates FLAC file metadata with artist, album artist, and album information.

Author: Jason Evans
Date: 2026-01-10
"""

import sys
import os
import sqlite3
import glob
import re
import music_tag
from pathlib import Path
from dateutil.parser import parse
from typing import Optional, Tuple


class MetadataUpdater:
    """Handles metadata updates for concert recording archives."""
    
    # Known microphone types to identify audience recordings
    MICROPHONE_TYPES = [
        "nak", "sony", "schoeps", "mk41", "mk4", "km84i", "km184", "km140",
        "ccm", "cmc", "akg", "senn", "mg", "m210", "m201", "at4053", "re20",
        "cemc", "ck41", "bk4011", "rsm191", "beyer", "m88"
    ]
    
    # Iconic names (add more if you desire)
    ICONIC_NAMES = [
        "Miller"
    ]
    
    def __init__(self, database_path: str):
        """Initialize the metadata updater.
        
        Args:
            database_path: Path to the SQLite database file
        """
        self.db_path = database_path
        self.connection = None
        self.cursor = None
        self.skip_version = False  # Will be set from command line argument
        self.setup_logging()
    
    def setup_logging(self):
        """Create log directory and file paths."""
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        self.logs = {
            'no_flac_files_in_folder': self.log_dir / "no_flac_files_in_folder_log.txt",
            'date_not_found': self.log_dir / "date_not_found_log.txt",
            'no_recording_version_found': self.log_dir / "no_recording_version_found_log.txt",
            'no_shnid_found': self.log_dir / "no_shnid_found_log.txt",
            'multiple_shows_same_date': self.log_dir / "multiple_shows_same_date.txt",
            'song_count_mismatch': self.log_dir / "song_count_mismatch.txt"
        }
        
        # Clear existing log files
        for log_file in self.logs.values():
            if log_file.exists():
                log_file.unlink()
    
    def log(self, log_type: str, message: str):
        """Write a message to the specified log file.
        
        Args:
            log_type: Type of log (e.g., 'no_flac_files_in_folder', 'date_not_found')
            message: Message to log
        """
        if log_type in self.logs:
            with open(self.logs[log_type], 'a') as f:
                f.write(f"{message.strip()}\n")
    
    def connect_database(self):
        """Establish database connection."""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
    
    def close_database(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
    
    def validate_artist(self, artist: str) -> bool:
        """Check if artist exists in database.
        
        Args:
            artist: Artist name to validate
            
        Returns:
            True if artist exists, False otherwise
        """
        sql = "SELECT * FROM acts WHERE name = ?;"
        self.cursor.execute(sql, (artist,))
        return len(self.cursor.fetchall()) > 0
    
    def extract_date(self, folder_name: str) -> Optional[Tuple[int, int, int]]:
        """
        Search for a date in YYYY-MM-DD or YY-MM-DD format in a string.
        
        Args:
            folder_name: The string to search for a date
            
        Returns:
            A tuple of (year, month, day) as integers with 4-digit year,
            or None if no date is found.
            For YY-MM-DD format, assumes 20YY for years 00-29 and 19YY for years 30-99.
        """
        pattern = r'(?<!\d)(\d{2}|\d{4})-(\d{2})-(\d{2})(?!\d)'
        
        match = re.search(pattern, folder_name)
        
        if match:
            year_str = match.group(1)
            month = int(match.group(2))
            day = int(match.group(3))
            
            # Convert 2-digit year to 4-digit year
            if len(year_str) == 2:
                year = int(year_str)
                # Common convention: 00-29 -> 2000-2029, 30-99 -> 1930-1999
                if year <= 29:
                    year += 2000
                else:
                    year += 1900
            else:
                year = int(year_str)
            
            return (year, month, day)
        
        return None
    
    def determine_version(self, folder_name: str) -> str:
        """Determine recording version/source from folder name.
        
        Args:
            folder_name: Folder name to parse
            
        Returns:
            Version string (e.g., 'sbd', 'aud', 'mtx')
        """
        folder_lower = folder_name.lower()
        
        # Check in priority order
        if "mtx" in folder_lower:
            return "mtx"
        elif "sbd" in folder_lower:
            return "sbd"
        elif "aud" in folder_lower:
            return "aud"
        elif any(mic in folder_lower for mic in self.MICROPHONE_TYPES):
            return "aud"
        elif "fm" in folder_lower:
            return "fm"
        elif "tv" in folder_lower:
            return "tv"
        elif "fob" in folder_lower:
            return "fob"
        elif "studio" in folder_lower:
            return "studio"
        elif "gmb" in folder_lower:
            return "gmb"
        elif "pa" in folder_lower and "panic" not in folder_lower:
            return "pa"
        elif "5-1" in folder_lower:
            # Check all occurrences of "5-1" to find one that's not part of a date
            start = 0
            found_surround = False
            while True:
                idx = folder_lower.find("5-1", start)
                if idx == -1:
                    break
                # If "5-1" is not preceded by a digit, it's likely the surround indicator
                if idx == 0 or not folder_lower[idx-1].isdigit():
                    found_surround = True
                    break
                start = idx + 1
            if found_surround:
                return "5.1"
        elif "dts" in folder_lower:
            return "dts"
        
        return ""
    
    def extract_shnid(self, folder_name: str) -> str:
        """Extract SHNID (show identifier) from folder name.
        
        Args:
            folder_name: Folder name to parse
            
        Returns:
            SHNID string if found, empty string otherwise
        """
        words = folder_name.split(".")
        for word in words:
            try:
                return str(int(word))
            except ValueError:
                continue
        return ""
    
    def search_names(self, folder_name: str) -> str:
        """Determine any iconic names exist in the folder name.
        
        Args:
            folder_name: Folder name to parse
            
        Returns:
            Name (e.g., 'Miller')
        """
        folder_lower = folder_name.lower()
        
        if any(name.lower() in folder_lower for name in self.ICONIC_NAMES):
            return next(name for name in self.ICONIC_NAMES if name.lower() in folder_lower)
            
        return ""
    
    def get_event_number(self, artist: str, year: int, month: int, day: int) -> int:
        """Get event number for a specific date.
        
        Args:
            artist: Artist name
            year: Year of event
            month: Month of event
            day: Day of event
            
        Returns:
            Event number or None if not found or multiple events exist
        """
        sql = """
            SELECT events.event_no
            FROM acts
            INNER JOIN events ON acts.ID = events.act_id
            WHERE acts.name_search = ? AND events.year = ? 
                AND events.month = ? AND events.day = ?;
        """
        
        self.cursor.execute(sql, (artist, year, month, day))
        rows = self.cursor.fetchall()
        
        if len(rows) == 0:
            return None
        elif len(rows) > 1:
            return -1  # Multiple shows indicator
        else:
            return rows[0][0]
    
    def get_show_data(self, artist: str, year: int, month: int, day: int, event_no: int) -> list:
        """Retrieve complete show data from database.
        
        Args:
            artist: Artist name
            year: Year of event
            month: Month of event
            day: Day of event
            event_no: Event number
            
        Returns:
            List of rows containing show data
        """
        # [0] name | [1] genre | [2] Year | [3] Month | [4] Day | [5] venue1 | [6] venue2 | [7] venue3
        # [8] venue4 | [9] venue5 | [10] set | [11] song | [12] segue
        sql = """
            SELECT acts.name, acts.genre,
                   events.Year, events.Month, events.Day,
                   venues.venue1, venues.venue2, venues.venue3, venues.venue4, venues.venue5,
                   event_sets."set", songs.song, event_songs.segue
            FROM venues
            INNER JOIN (songs
                INNER JOIN ((acts
                    INNER JOIN events ON acts.ID = events.act_id)
                    INNER JOIN (event_sets
                        INNER JOIN event_songs ON event_sets.id = event_songs.event_set_id)
                    ON events.ID = event_sets.event_id)
                ON songs.ID = event_songs.song_id)
            ON venues.ID = events.venue_id
            WHERE events.Year = ? AND events.Month = ? AND events.Day = ?
                AND acts.name_search = ? AND events.event_no = ?
            ORDER BY event_sets.seq, event_songs.seq, events.event_no;
        """
        print(artist + " " + str(year) + " " + str(month) + " " + str(day) + " " + str(event_no))
        self.cursor.execute(sql, (year, month, day, artist, event_no))
        return self.cursor.fetchall()
    
    def build_location_string(self, venue_parts: tuple) -> str:
        """Build location string from venue data.
        
        Args:
            venue_parts: Tuple of venue components (venue1-5)
            
        Returns:
            Formatted location string
        """
        location_parts = [str(part) for part in venue_parts[:5] if part]
        return ", ".join(location_parts)
    
    def build_album_name(self, year: int, month: int, day: int, version: str, shnid: int, name: str, location: str) -> str:
        """Build album name in standardized format.
        
        Args:
            year: Year of show
            month: Month of show
            day: Day of show
            version: Recording version/source
            shnid: shnid of show, if found
            name: Iconic taper name, if found
            location: Venue location string
            
        Returns:
            Formatted album name
        """
        
        date_str = f"{year}-{month:02d}-{day:02d}"
        parts = [p for p in [version, shnid, name] if p]
        version_str = f"({' '.join(parts)})" if parts else ""
        return f"{date_str} {version_str} {location}"
    
    def update_file_metadata(self, files: list, artist: str, album: str, genre: str, year: int):
        """Update metadata for all FLAC files.
        
        Args:
            files: List of file paths
            artist: Artist name
            album: Album name
            year: Year of recording
        """
        for index, file_path in enumerate(files):
            audio = music_tag.load_file(file_path)
            audio["artist"] = artist
            audio["albumartist"] = artist
            audio["album"] = album
            audio["genre"] = genre
            audio["year"] = year
            audio.raw["tracknumber"] = f"{index + 1:02d}"
            audio.raw["discnumber"] = None
            audio.save()
    
    def create_setlists(self, folder_path: Path, show_data: list, flac_count: int):
        """Create setlist files from show data.
        
        Args:
            folder_path: Path to folder where setlists will be created
            show_data: List of rows containing set and song information
            flac_count: Number of FLAC files in the folder
        """
        set_setlist_path = folder_path / "set_setlist.txt"
        setlist_path = folder_path / "setlist.txt"
        
        # Remove existing setlist files
        for path in [set_setlist_path, setlist_path]:
            if path.exists():
                path.unlink()
        
        current_set = ""
        set_lines = []
        regular_lines = []
        
        # Add file count as first line in setlist.txt
        regular_lines.append("# " + str(flac_count))
        
        for row in show_data:
            set_number = row[10]
            song_title = row[11]
            is_segue = row[12] == 1
            
            # Add segue indicator
            if is_segue:
                song_title += " >"
            
            # Add set header if changed
            if current_set != set_number:
                current_set = set_number
                set_lines.append(set_number)
            
            set_lines.append(song_title)
            regular_lines.append(song_title)
        
        # Write files without trailing newline
        with open(set_setlist_path, 'w') as set_file:
            set_file.write('\n'.join(set_lines))
        
        with open(setlist_path, 'w') as regular_file:
            regular_file.write('\n'.join(regular_lines))
    
    def process_folder(self, folder_path: Path, artist: str):
        """Process a single folder and update metadata.
        
        Args:
            folder_path: Path to folder to process
            artist: Artist name
        """
        folder_name = folder_path.name
        print(f"\nProcessing folder: {folder_name}")
        
        # Extract date
        date_parts = self.extract_date(folder_name)
        if not date_parts:
            print(f"  ❌ No date found in folder name")
            self.log('date_not_found', folder_name)
            return
        
        year, month, day = date_parts
        print(f"  ✓ Date found: {year}-{month:02d}-{day:02d}")
        
        # Determine recording version
        if self.skip_version:
            version = ""
            print(f"  ⚠ Version detection skipped (skip_version=1)")
        else:
            version = self.determine_version(folder_name)
            if not version:
                print(f"  ⚠ No recording version found")
                self.log('no_recording_version_found', folder_name)
            else:
                print(f"  ✓ Version: {version}")
        
        # Extract SHNID
        shnid = self.extract_shnid(folder_name)
        if not shnid:
            print(f"  ⚠ No SHNID found")
            self.log('no_shnid_found', folder_name)
        else:
            print(f"  ✓ SHNID: {shnid}")
        
        # Search for iconic names
        name = self.search_names(folder_name)
        if name:
            print(f"  ✓ Name: {name}")
        
        # Get event number
        event_no = self.get_event_number(artist, year, month, day)
        if event_no is None:
            print(f"  ❌ Event not found in database")
            self.log('date_not_found', folder_name)
            return
        elif event_no == -1:
            print(f"  ❌ Multiple shows found for this date")
            self.log('multiple_shows_same_date', folder_name)
            return
        
        print(f"  ✓ Event number: {event_no}")
        
        # Get show data
        show_data = self.get_show_data(artist, year, month, day, event_no)
        if not show_data:
            print(f"  ❌ No show data found")
            self.log('date_not_found', folder_name)
            return
        
        print(f"  ✓ Found {len(show_data)} songs in database")
        
        # Get FLAC files
        flac_files = sorted(folder_path.glob("*.flac"))
        if not flac_files:
            print(f"  ❌ No FLAC files found")
            self.log('no_flac_files_in_folder', folder_name)
            return
        
        print(f"  ✓ Found {len(flac_files)} FLAC files")
        
        # Check file count
        if len(show_data) != len(flac_files):
            print(f"  ⚠ Song count mismatch: {len(show_data)} in DB vs {len(flac_files)} files")
            self.log('song_count_mismatch', folder_name)
        
        # Genre
        genre = show_data[0][1]
        
        # Build album name
        location = self.build_location_string(show_data[0][5:10])
        album = self.build_album_name(year, month, day, version, shnid, name, location)
        print(f"  ✓ Album: {album}")
        
        # Update metadata
        print(f"  ✓ Updating metadata...")
        self.update_file_metadata(flac_files, artist, album, genre, year)
        
        # Create setlists
        print(f"  ✓ Creating setlists...")
        self.create_setlists(folder_path, show_data, len(flac_files))
        
        print(f"  ✅ Complete!")
    
    
    def display_log_summary(self):
        """Display a summary of all log entries at the end of processing."""
        print("\n" + "=" * 80)
        print("LOG SUMMARY")
        print("=" * 80)
        
        has_entries = False
        
        for log_name, log_path in self.logs.items():
            if log_path.exists():
                with open(log_path, 'r') as f:
                    entries = f.readlines()
                
                if entries:
                    has_entries = True
                    # Format log name for display
                    display_name = log_name.replace('_', ' ').title()
                    print(f"\n{display_name} ({len(entries)} entries):")
                    print("-" * 80)
                    for entry in entries:
                        print(f"  • {entry.strip()}")
        
        if not has_entries:
            print("\n✓ No issues found! All folders processed successfully.")
        
        print("\n" + "=" * 80)
    
    
    def process_directory_tree(self, root_path: Path, artist: str):
        """Recursively process all folders in directory tree.
        
        Args:
            root_path: Root directory to process
            artist: Artist name
        """
        print(f"Processing: {root_path}")
        
        # Process the root path itself if it's a directory
        if root_path.is_dir():
            self.process_folder(root_path, artist)
        
        # Then process all subdirectories
        for folder_path in root_path.rglob("*"):
            if folder_path.is_dir() and folder_path != root_path:
                self.process_folder(folder_path, artist)


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python metadata_step_1.py <Artist Name> <Directory Path> [skip_version]")
        print("\nArguments:")
        print("  Artist Name:     Artist name to query (case sensitive, use quotes)")
        print("  Directory Path:  Top-level directory path (full path, use quotes)")
        print("                   Accepts both Unix (/) and Windows (\\) path separators")
        print("  skip_version:    Optional - Set to 1 to skip recording version detection (default: 0)")
        print("\nExample:")
        print('  python metadata_step_1.py "Grateful Dead" "/path/to/music"')
        print('  python metadata_step_1.py "Grateful Dead" "C:\\Music\\Grateful Dead"')
        print('  python metadata_step_1.py "Grateful Dead" "/path/to/music" 1')
        sys.exit(1)
    
    artist = sys.argv[1]
    directory_path = Path(sys.argv[2])
    skip_version = int(sys.argv[3]) if len(sys.argv) == 4 else 0
    
    # Validate directory
    if not directory_path.exists():
        print(f"Error: Directory not found: {directory_path}")
        sys.exit(1)
    
    # Initialize updater
    updater = MetadataUpdater("show_data.db")
    updater.skip_version = (skip_version == 1)
    
    try:
        # Connect to database
        updater.connect_database()
        
        # Validate artist
        if not updater.validate_artist(artist):
            print(f"Error: Artist '{artist}' not found in database.")
            sys.exit(1)
        
        print(f"Artist: {artist}")
        print(f"Skip Version Detection: {'Yes' if updater.skip_version else 'No'}")
        
        # Process directory tree
        updater.process_directory_tree(directory_path, artist)
                
        # Display log summary
        updater.display_log_summary()
        
    finally:
        updater.close_database()


if __name__ == "__main__":
    main()