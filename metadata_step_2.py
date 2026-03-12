#!/usr/bin/env python3
"""
Audio Metadata Step 2 - Song Title Updater

Reads setlist.txt files from folders and updates FLAC file metadata with song titles.
Each line in setlist.txt corresponds to one FLAC file in sequence.

Author: Jason Evans
Date: 2026-02-03
"""

import sys
from pathlib import Path
import music_tag


class MetadataTitleUpdater:
    """Updates FLAC file titles from setlist files."""
    
    SETLIST_FILENAME = "setlist.txt"
    
    def __init__(self, root_path: Path):
        """Initialize the metadata updater.
        
        Args:
            root_path: Root directory to process recursively
        """
        self.root_path = Path(root_path)
        
        if not self.root_path.exists():
            raise ValueError(f"Directory not found: {self.root_path}")
        
        if not self.root_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.root_path}")
        
        self.setup_logging()
    
    def setup_logging(self):
        """Create log directory and file paths."""
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        self.logs = {
            'count_mismatch': self.log_dir / "count_mismatch.txt",
            'setlist_not_exist': self.log_dir / "setlist_not_exist.txt"
        }
        
        # Track error counts for summary
        self.error_counts = {
            'count_mismatch': 0,
            'setlist_not_exist': 0
        }
        
        # Clear existing log files
        for log_file in self.logs.values():
            if log_file.exists():
                log_file.unlink()
    
    def log(self, log_type: str, message: str):
        """Write a message to the specified log file.
        
        Args:
            log_type: Type of log ('count_mismatch' or 'setlist_not_exist')
            message: Message to log
        """
        if log_type in self.logs:
            with open(self.logs[log_type], 'a') as f:
                f.write(f"{message.strip()}\n")
            self.error_counts[log_type] += 1
    
    def read_setlist(self, setlist_path: Path) -> list:
        """Read and parse setlist file.
        
        Args:
            setlist_path: Path to setlist.txt file
            
        Returns:
            List of song titles (non-empty lines, excluding comments)
        """
        with open(setlist_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out empty lines, comments (starting with #), and strip whitespace
        return [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
    
    def display_error_summary(self):
        """Display summary of logged errors at the end of processing."""
        print("\n" + "=" * 70)
        print("ERROR SUMMARY")
        print("=" * 70)
        
        total_errors = sum(self.error_counts.values())
        
        if total_errors == 0:
            print("\n✓ No errors! All folders processed successfully.\n")
            return
        
        print(f"\nTotal folders with issues: {total_errors}\n")
        
        # Display count mismatch errors
        if self.error_counts['count_mismatch'] > 0:
            print(f"📊 Count Mismatches: {self.error_counts['count_mismatch']}")
            print("-" * 70)
            log_file = self.logs['count_mismatch']
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        print(f"  • {line.strip()}")
            print()
        
        # Display missing setlist errors
        if self.error_counts['setlist_not_exist'] > 0:
            print(f"📝 Missing setlist.txt: {self.error_counts['setlist_not_exist']}")
            print("-" * 70)
            log_file = self.logs['setlist_not_exist']
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        print(f"  • {line.strip()}")
            print()
        
        print("=" * 70)
        print(f"Check the 'logs' folder for detailed error logs.\n")
    
    def update_file_titles(self, flac_files: list, setlist: list):
        """Update title metadata for FLAC files.
        
        Args:
            flac_files: List of FLAC file paths
            setlist: List of song titles
        """
        for file_path, title in zip(flac_files, setlist):
            try:
                audio = music_tag.load_file(file_path)
                audio["title"] = title
                audio.save()
                print(f"  ✓ {file_path.name}: {title}")
            except Exception as e:
                print(f"  ✗ Error updating {file_path.name}: {e}")
    
    def process_folder(self, folder_path: Path):
        """Process a single folder and update FLAC titles from setlist.
        
        Args:
            folder_path: Path to folder containing FLAC files and setlist
        """
        folder_name = folder_path.name
        print(f"\n{folder_name}")
        
        # Check for setlist file
        setlist_path = folder_path / self.SETLIST_FILENAME
        if not setlist_path.exists():
            self.log('setlist_not_exist', folder_name)
            print(f"  ⚠ No setlist.txt found")
            return
        
        # Get all FLAC files
        flac_files = sorted(folder_path.glob("*.flac"))
        if not flac_files:
            print(f"  ⚠ No FLAC files found")
            return
        
        # Read setlist
        try:
            setlist = self.read_setlist(setlist_path)
        except Exception as e:
            print(f"  ✗ Error reading setlist: {e}")
            return
        
        # Check counts match
        if len(flac_files) != len(setlist):
            self.log('count_mismatch', 
                    f"{folder_name} (FLAC: {len(flac_files)}, Setlist: {len(setlist)})")
            print(f"  ⚠ Count mismatch: {len(flac_files)} FLAC files, {len(setlist)} setlist entries")
            return
        
        # Update titles
        self.update_file_titles(flac_files, setlist)
    
    def process_all(self):
        """Recursively process all folders in the directory tree."""
        print(f"Processing: {self.root_path}")
        
        # Process root directory
        self.process_folder(self.root_path)
        
        # Process all subdirectories
        for folder_path in self.root_path.rglob("*"):
            if folder_path.is_dir():
                self.process_folder(folder_path)
        
        print("\n✓ Processing complete!")
        
        # Display error summary
        self.display_error_summary()


def main():
    """Main entry point for the script."""
    if len(sys.argv) != 2:
        print("Usage: python metadata_step_2.py <directory_path>")
        print("\nArguments:")
        print("  directory_path: Top-level directory to process recursively")
        print("\nDescription:")
        print("  Updates FLAC file titles from setlist.txt files in each folder.")
        print("  Each line in setlist.txt becomes the title for the corresponding FLAC file.")
        print("\nExample:")
        print('  python metadata_step_2.py "/path/to/music/folder"')
        sys.exit(1)
    
    directory_path = sys.argv[1]
    
    try:
        updater = MetadataTitleUpdater(directory_path)
        updater.process_all()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()