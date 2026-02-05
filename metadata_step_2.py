

metadata_step_1.py
229 lines

py

Can this script be cleaned up?

Jan 31
I'll review this script and suggest improvements for readability, maintainability, and Python best practices.


Created a file, read a file
Yes! I've refactored your script with significant improvements:

Key Improvements
1. Object-Oriented Design

Created a MetadataUpdater class to encapsulate all functionality
Better organization and easier to test/maintain
2. Type Hints & Documentation

Added type hints for all parameters
Comprehensive docstrings for all methods
Clear module-level documentation
3. Better Path Handling

Used pathlib.Path throughout instead of string manipulation
More robust and platform-independent
4. Improved Error Handling

Separated concerns into smaller methods
Easier to debug and extend
5. Code Readability

Removed magic numbers and hardcoded values
Named constants (e.g., MICROPHONE_TYPES)
Clearer variable names
Better SQL formatting
6. Simplified Logic

Removed redundant operations
Consolidated file operations
Cleaner logging mechanism using dictionary
7. Better Main Function

Improved command-line help
Better argument validation
Proper try/finally for database cleanup
The refactored version maintains all original functionality while being much more maintainable and Pythonic!

Metadata step 1 cleaned
PY 

nugs_dl_cleanup.py
29 lines

py

check and clean this script up

Feb 3

Created a file, read a file
I've cleaned up your script and fixed several critical bugs:

Critical Bugs Fixed
path = path("N:\# Temp #\nugsdl") - This would crash! Should be Path() with capital P
Hardcoded path - Now uses command-line argument for flexibility
Unused glob imports - The script imported glob but used Path.glob() inconsistently
Index enumeration - Used enumerate(files) but then referenced files[index] redundantly
Major Improvements
1. Object-Oriented Design

Created NugsCleanup class for better organization
Separated concerns into logical methods
2. Better Path Handling

Consistent use of pathlib.Path throughout
No more mixing string paths and Path objects
Removed unnecessary os.chdir() calls
3. Error Handling

Try/except blocks for file processing
Validation of directory existence
Informative error messages
4. Cleaner Code

Removed redundant variables (search_pattern, extension)
Used enumerate(start=1) for clearer intent
Better variable names
5. User Experience

Command-line argument support
Progress feedback during processing
Clear usage instructions
6. Documentation

Module docstring
Method docstrings with type hints
Comments where helpful
The refactored version is more robust, maintainable, and won't crash like the original!

Nugs dl cleanup cleaned
PY 

nugs_dl_cleanup.py
29 lines

py

clean up this script

Feb 3

Created 2 files, ran a command, read a file
I've cleaned up your script and fixed several critical bugs:

Critical Bugs Fixed
path = path("N:\# Temp #\nugsdl") - This would crash immediately! Should be Path() with capital P
Hardcoded path - Now accepts command-line argument for flexibility
Redundant code - Imported both os.walk and glob, but used them inefficiently
Unnecessary os.chdir() - Risky and unnecessary with proper path handling
Key Improvements
1. Object-Oriented Structure

Encapsulated logic in NugsCleanup class
Better organization and reusability
2. Modern Path Handling

Uses pathlib.Path exclusively and correctly
No directory changes needed
3. Error Handling

Validates directory exists
Catches errors per file (won't crash entire run if one file fails)
Informative error messages
4. Better Code Quality

Removed unused imports (os, glob)
Fixed enumerate usage (was redundant with files[index])
Cleaner, more readable logic
5. User Experience

Command-line argument support
Progress feedback
Clear usage instructions
6. Documentation

Proper docstrings throughout
Type hints for better IDE support
The refactored version fixes the bugs and is much more maintainable!

Nugs dl cleanup cleaned
PY 
modify to hard code path to "N:\# Temp #\nugsdl"

Feb 3

Edited a file, read a file
Done! I've modified the script to hardcode the path to N:\# Temp #\nugsdl. Now you can simply run it without any command-line arguments:

bash
python nugs_dl_cleanup_cleaned.py
The path is properly escaped using a raw string (r"N:\# Temp #\nugsdl") to handle the backslashes correctly.

Nugs dl cleanup cleaned
PY 

metadata_step_2.py
63 lines

py

can this script be cleaned up

2:04 PM

Created a file, read a file
Yes! I've cleaned up your script with significant improvements:

Key Improvements
1. Object-Oriented Design

Created TitleUpdater class for better organization
Encapsulated all functionality in logical methods
2. Better Path Handling

Uses pathlib.Path exclusively instead of mixing os.path and string operations
Removed unnecessary os.chdir() calls
More robust and platform-independent
3. Improved Error Handling

Try/except blocks for file operations
Better error messages with context
Won't crash on single file errors
4. Code Simplification

Removed redundant code (glob pattern setup, unnecessary variables)
Fixed the enumerate redundancy (was using both file and files[index])
Cleaner setlist reading with proper filtering
5. Better Logging

More informative log messages (includes file/setlist counts for mismatches)
Using context managers for file operations
Added UTF-8 encoding for setlist reading
6. User Experience

Visual indicators (✓, ✗, ⚠) for progress feedback
Shows what title each file is being updated to
Clear usage instructions
Better summary at completion
7. Documentation

Comprehensive docstrings
Type hints throughout
Clear module-level documentation
The refactored version is much cleaner, more maintainable, and provides better feedback during operation!

Metadata step 2 cleaned
PY 


Want to be notified when Claude responds?


Claude is AI and can make mistakes. Please double-check responses.
Metadata step 2 cleaned · PY
Copy

#!/usr/bin/env python3
"""
Audio Metadata Title Updater

Reads setlist.txt files from each folder and updates FLAC file titles
to match the song names in the setlist.

Author: Jason Evans
"""

import sys
from pathlib import Path
import music_tag


class TitleUpdater:
    """Handles updating FLAC file titles from setlist files."""
    
    SETLIST_FILENAME = "setlist.txt"
    
    def __init__(self, root_path: Path):
        """Initialize the title updater.
        
        Args:
            root_path: Root directory to process
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
        
        # Clear existing log files
        for log_file in self.logs.values():
            if log_file.exists():
                log_file.unlink()
    
    def log(self, log_type: str, message: str):
        """Write a message to the specified log file.
        
        Args:
            log_type: Type of log (e.g., 'count_mismatch', 'setlist_not_exist')
            message: Message to log
        """
        if log_type in self.logs:
            with open(self.logs[log_type], 'a') as f:
                f.write(f"{message.strip()}\n")
    
    def read_setlist(self, setlist_path: Path) -> list:
        """Read and parse setlist file.
        
        Args:
            setlist_path: Path to setlist.txt file
            
        Returns:
            List of song titles (non-empty lines only)
        """
        with open(setlist_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out empty lines and strip whitespace
        return [line.strip() for line in lines if line.strip()]
    
    def process_folder(self, folder_path: Path):
        """Process a single folder and update FLAC titles.
        
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
            print(f"  No FLAC files found")
            return
        
        # Read setlist
        try:
            setlist = self.read_setlist(setlist_path)
        except Exception as e:
            print(f"  Error reading setlist: {e}")
            return
        
        # Check counts match
        if len(flac_files) != len(setlist):
            self.log('count_mismatch', 
                    f"{folder_name} - Files: {len(flac_files)}, Setlist: {len(setlist)}")
            print(f"  ⚠ Count mismatch: {len(flac_files)} files, {len(setlist)} songs")
            return
        
        # Update titles
        for index, file_path in enumerate(flac_files):
            try:
                audio = music_tag.load_file(file_path)
                audio["title"] = setlist[index]
                audio.save()
                print(f"  ✓ {file_path.name} → {setlist[index]}")
            except Exception as e:
                print(f"  ✗ Error processing {file_path.name}: {e}")
    
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
        print(f"\nCheck the '{self.log_dir}' folder for any issues.")


def main():
    """Main entry point for the script."""
    if len(sys.argv) != 2:
        print("Usage: python metadata_step_2.py <directory_path>")
        print("\nArguments:")
        print("  directory_path: Top-level directory to process (recursive)")
        print("\nDescription:")
        print("  Reads setlist.txt from each folder and updates FLAC file titles")
        print("  to match the song names in the setlist.")
        print("\nExample:")
        print('  python metadata_step_2.py "/path/to/music"')
        sys.exit(1)
    
    directory_path = sys.argv[1]
    
    try:
        updater = TitleUpdater(directory_path)
        updater.process_all()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
