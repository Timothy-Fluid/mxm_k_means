# get_tfidf.py
# create a tfidf cooefficient for each row in the lyrics database

trace = None
try:
    from IPython.core.debugger import Tracer; trace = Tracer()
except ImportError:
    def disabled(): dbg("Tracepoint disabled -- IPython not found")
    trace = disabled

from math import log
import sqlite3
import sys

class TFIDFCounter(object):
    def __init__(self, dbh):
        self.dbh = dbh
        self.words = {}
        self.totaldocs = 0
        self._init_totals_for_words()

    def _init_totals_for_words(self):
        dbg("Initializing document frequency totals...")
        c = self.dbh.cursor()
        for row in c.execute("SELECT word, COUNT(track_id) FROM lyrics GROUP BY word"):
            self.words[row[0]] = row[1]
        c.execute("SELECT COUNT(DISTINCT(track_id)) from lyrics")
        self.totaldocs = float(c.fetchone()[0])

    def calc_tfidf(self, track_id):

        tfidf = []
        words_in_song = []
        total_words = 0

        # get all words in a given song
        c = self.dbh.cursor()
        for row in c.execute("SELECT word, count FROM lyrics WHERE track_id = ?", (track_id,)):
            words_in_song.append(row)
            total_words += row[1]
        total_words = float(total_words)
        # calculate tfidf
        for word,count in words_in_song:
            tf = count / total_words
            idf = log ( self.totaldocs / self.words[word] )
            tfidf.append((word,tf * idf))

        return tfidf

def init_output_db(dbh):
    # create the tfidf table
    c = dbh.cursor()
    c.execute("DROP TABLE IF EXISTS tfidf")
    c.execute('''CREATE TABLE tfidf
              (track_id text,
               word text,
               tfidf real)''')
	c.execute("CREATE INDEX idx_track_id ON tfidf (track_id)")
	c.execute("CREATE INDEX idx_word ON tfidf (word)")
    dbh.commit()

def main(input_db="mxm_dataset.db", output_db="mxm_tfidf.db"):
    # load the databases
    dbg("Connecting to musixmatch database: {}".format(input_db))
    mxm = sqlite3.connect(input_db)
    dbg("Connecting to output database: {}".format(output_db))
    out = sqlite3.connect(output_db)

    dbg("Creating output tables in {}".format(output_db))
    init_output_db(out) 
    tdc = TFIDFCounter(mxm)

    trace()
    # calculate the tfidf for all documents
    dbg("Begin calculating TFIDF...")
    compl = 0
    tenpcnt = int(tdc.totaldocs / 100)
    c = mxm.cursor()
    d = out.cursor()
    query = "INSERT INTO tfidf VALUES ( ?, ?, ? )"
    for row in c.execute ("SELECT DISTINCT(track_id) FROM lyrics"):
        track_id = row[0]
        for word, tfidf in tdc.calc_tfidf(track_id):
            d.execute(query, (track_id, word, tfidf))
        compl += 1
        if (compl % tenpcnt == 0):
            print ("{:.2%} complete".format(compl / tdc.totaldocs))
    out.commit()
    print ("Processed {} tracks".format(compl))

def dbg(message):
    sys.stderr.write(message + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(input_db=sys.argv[1])
    elif len(sys.argv) > 2:
        main(input_db=sys.argv[1], output_db=sys.argv[2])
