# sierra-patron-loads
Python script to bulk find/create/update patron records in Sierra for use with LibraryNow/school partnerships

Check data formats and column names to match what is in the script.

The process is broken into 3 files:
1. sort-patrons.py: attempt to find a matching patron by student ID and sort students into new lists by creation vs update (or other exception cases based on data in Sierra)
2. create-patrons.py: creates patrons using provided student data
3. update-patrons.py: updates patrons using provided student data

These steps could be combined if there is a smaller dataset, otherwise recommend splitting up into batches given limitations on the Sierra API ("Remote end closed connection without response" error).
