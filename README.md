# **Live-Music-Tagging**
This is a series of scripts used to tag live music shows.

## **show_data.db**
SQLite database used to store live show data. Database is currently populated with all Grateful Dead, Jerry Garcia, and Widespread Panic shows. Would love to add other artists as I find available data and/or websites to scrape. Caveat, the script currently doesn't handle instances where an artist performs > 1 show in the same day. Check log files for those occurrances.

## **metadata_step_1.py**
> python3 metadata_step_1.py "Artist" "Recursive Folder Path"

Current supported artists:
1. Grateful Dead
2. Jerry Garcia (based on show date, looks up actual Jerry Garcia project)
3. Widespread Panic

The folder must contain the show date somewhere in the folder in one of the following formats: YYYY-MM-DD, YY-MM-DD

The show album will follow the following format: YYYY-MM-DD (sbd/aud/fm/tv/fob/studio/gmb/pa/mtx [Miller] [shnid]) Venue, City, State
The following tags will be set:
1. artist
2. albumartist
3. album
4. genre
5. year
6. tracknumber (01 to NN, does not consider set number)
7. discnumber (set to NULL)

Additionally, this script will place 2 files in each show folder: set_setlist.txt, setlist.txt

### **set_setlist.txt** ###
This file is for informational purposes.

1\
Ain't Life Grand >\
Pleas >\
Tall Boy >\
Little By Little\
Hatfield\
Steven's Cat\
Rebirtha >\
Ribs And Whiskey\
Saint Ex\
2\
Walkin' (For Your Love)\
Greta >\
I'm Not Alone\
Fishing >\
Travelin' Man >\
The Waker\
Surprise Valley >\
Drums >\
Surprise Valley\
Junior\
Genesis\
Bowlegged Woman >\
Love Tractor\
E\
Keep Me in Your Heart\
Red Hot Mama\


### **setlist.txt** ###
This file is created based on the database entries of the show. For audience recordings primarily, the digitizer adds "filler" tracks as they see fit. Prime example being crowd/tuning tracks. The goal of this file is to open it side-by-side with the taper/digitizer's text file which details aspects of the recording, including the track list. You can modify this file by adding/combining/removing entries to match the particular recording of the show. For convenience, the file starts with a "# <number>" which represents the number of flac files in the folder. This can help with a quick sanity check. Since the line starts with #, it will be ignored by metadata_step_2.py.

\# 24\
Ain't Life Grand >\
Pleas >\
Tall Boy >\
Little By Little\
Hatfield\
Steven's Cat\
Rebirtha >\
Ribs And Whiskey\
Saint Ex\
Walkin' (For Your Love)\
Greta >\
I'm Not Alone\
Fishing >\
Travelin' Man >\
The Waker\
Surprise Valley >\
Drums >\
Surprise Valley\
Junior\
Genesis\
Bowlegged Woman >\
Love Tractor\
Keep Me in Your Heart\
Red Hot Mama\

## **metadata_step_2.py**
> python3 metadata_step_2.py "Recursive Folder Path"

Once you are satisfied with the contents of setlist.txt, run this script to commit the song titles to the flac metadata.
