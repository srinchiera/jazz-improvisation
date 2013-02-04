from music21 import *
from itertools import product
import os
import glob
import random
import shlex

class rhythm:
    ''' Our class rhythm stores the probability matrix of going from a note of
        duration i to a note of duration j. When initalized it builds this
        this information using data observed from the pieces provided in the
        corpus. The function new_note gives the ability to input some note 
        duration and using the probabilities obtained from the corpus, produces
        a new note duration.                                                '''

    matrix = []

    def __init__ (self, music_directory):
        ''' When initialized, a rythm object will create a matrix, represented
            as a list of lists that will contain the probabilities of going
            from one note duration to another. Element i,j of this matrix will
            represent going from a note of duration of i to a note of duration
            j. These lengths are increments of a sixteenth note and range from
            1 sixteenth note to a whole note. There is also a representation
            for an eight triplet and a sixteenth triplet. This matrix will be 
            of size 19x18, a row and column for every duration and an extra
            column for all the totals. Triplets are represented as one note.
            '''

        self.matrix = [[0 for x in range(19)] for y in range(18)] # fill matrix
                                                                  # with 0's
        # for every .xml file in our directory
        for infile in glob.glob(os.path.join(music_directory,'*.xml')):
   
            noteList = [] # running count of all the note durations
                          # encountered in the pieces, in order
            part = converter.parse(infile)[1] # 0th index is metadeta

            for measure in range (1,len(part)):
                tripcount = 0 # we keep track of which triplet of the three
                              # we are currently looking at.
                for note in part[measure].notesAndRests:
                    if (note.duration.quarterLength)*3 == 1: # if eigth triplet
                        if tripcount < 2: 
                            tripcount += 1
                        else:
                            noteList.append(17)
                            tripcount = 0
                    elif (note.duration.quarterLength)*6 == 1: # if 16 triplet
                        if tripcount < 2:
                            tripcount += 1
                        else:
                            noteList.append(18)
                            tripcount = 0

                    # If any notes are shorter than a sixteenth note, round up
                    # to a sixteenth. If any notes are longer than a whole note
                    # round up to a whole
                    elif (note.duration.quarterLength) * 4 < 1:
                        noteList.append(1)
                    elif (note.duration.quarterLength) > 16:
                        noteList.append(16)
                    else:
                        noteList.append(int(note.duration.quarterLength*4))

            for note in range(0,len(noteList)-1): # last note does is not
                                                  # followed by anything
                self.matrix[noteList[note]-1][noteList[note+1]-1] += 1
                self.matrix[noteList[note]-1][18] += 1 # increment total

        for row in self.matrix: # for each row, divide each element i,j by the
                                # row total to get the probability of going
                                # from i to j.
            if row [18] != 0:
                for duration in range(0,len(row)-1):
                    row[duration] = float(row[duration])/float(row[18])

    def new_note(self, old_note):
        ''' When given a note duration, new_note goes to that note's row in the
            probability matrix and traverses it until,  adding probabilities
            as it goes, until it reaches a uniformly chosen number between
            0 and 1. It returns this note as the next note of the sequence  '''

        randomNum = random.random() 
        total = 0
        row = self.matrix[old_note-1] # we subtract one because the caller sees
                                      # the sixteenth note as a value 1
                                      # duration, but it is in our matrix's
                                      # 0 row.
        
        for index in range(0,len(row)-1):
            if row[index] + total < randomNum: # stop when we have reached
                                               # random probability
                total += row[index]
            else:
                return index+1
                break

class pitches:
    ''' The pitch class holds the matrices for each chord class. Initializing
        a pitch object with a corpus will fill in these chord class matrices
        with the probabilities of going from some interval in a chord class to
        another. Pitch objects then have the ability to produce a new note when
        given some note and a chord by looking into the corresponding chord 
        class probabalistically finding the next interval, and then outputting 
        the corresponding note for the specific class.                       '''

    matrices = {"7": [], "fd": [], "aug7": [], "hd": [], "maj": [], "min": []}

    def __init__ (self, music_directory):
        '''
            Initializing an instance of a pitch class will fill in the matrices
            of each chord class. The rows and columns of this matrices represent
            intervals within the chord class and element A[i][j] represents the 
            probability of going from interval i to interval j. These 
            probabilities are calculated by seeing what has historically 
            happened in the pieces of our corpus, which are obtained from the 
            music_directory argument. Each matrix is size 14x13. The last
            column is reserved for storing how many intevals of that row have
            been inputted into the matrix in total                           '''

        for chordClass in self.matrices: # Initialize all of the matrices to 
                                         # 14x13 matrices filled with 0's
            self.matrices[chordClass] = [[0 for x in range(14)] for y in range(13)]
        
        # for every xml file in the directory
        for infile in glob.glob(os.path.join(music_directory,'*.xml')):

            # noteList stores a temporary run of intervals in each chord class
            # that is later used to update the matrix
            noteList = {"7": [], "fd": [], "aug7": [], \
                        "hd": [], "maj": [], "min": []}
            chordFile = open(str(infile)[:-3] + 'txt') # open corresponding 
                                                       # chord list.
            print "Reading " + str(infile) + "..."
            part = converter.parse(infile)[1] # open a music stream
    
            chordTonic, chordClass, remainingLength = \
                                    self.__parse_chord(chordFile)
            oldTonic = chordTonic
            for measure in range (1,len(part)): # iterate over all measures
                tmpTonic = chordTonic
                if measure > 1: # do not scan first chord twice
                    chordTonic, chordClass, remainingLength = \
                                          self.__parse_chord(chordFile)

                if chordTonic != oldTonic: # flush list on new chord
                    self.__list_to_matrix(noteList) # update matrix
                    noteList = {"7": [], "fd": [], "aug7": [], "hd": [], \
                                "maj": [], "min": []}
                    oldTonic = tmpTonic

                for note in part[measure].notesAndRests: # for notes in measure

                    if note.offset >= remainingLength: # if chord < 1 measure, 
                                                       # switch chords halfway
                                                       # through
                        tmpTonic = chordTonic
                        chordTonic, ChordClass, remainingLength = \
                                             self.__parse_chord(chordFile)
                        if chordTonic != oldTonic: # flush list on new chord
                            self.__list_to_matrixs(noteList)
                            noteList = {"7": [], "fd": [], "aug7": [], \
                                        "hd": [], "maj": [], "min": []}
                            oldTonic = tmpTonic

                    interval = self.__find_interval(chordTonic,note)
                    noteList[chordClass].append(interval)
            
            self.__list_to_matrix(noteList)
            chordFile.close()

        self.__normalize_matrices()

    def __parse_chord(self,chordFile):
        ''' Reads the a line from the chord file associated with a song and
            parses it to produce the chord tonic, the chord class, and the
            chord duration                                                   '''
        chord = shlex.split(chordFile.readline())
        return (chord[0],chord[1],chord[2])

    def __find_interval(self,root,note):
        ''' This function finds the interval between the root of a given
            chord and a note. If the note is a rest it returns an interval 
            of 12                                                           '''
        if note.isRest:
            return 12
        elif note.pitchClass - (pitch.Pitch(root)).pitchClass < 0:
            return note.pitchClass - (pitch.Pitch(root)).pitchClass + 12
        else:
            return note.pitchClass - (pitch.Pitch(root)).pitchClass

    def __list_to_matrix(self,noteList):
        ''' This function takes in the list containing the interval sequence
            observed for some chord class at some time in one of the corpus
            pieces. It scans through this interval sequence and it increments
            element i,j of a matrix if it observes the interval sequence
            i,j in our list                                                 '''
        
        for chord in noteList:
            for index in range(len(noteList[chord])-1): # leave out last note
                                                        # because it does not
                                                        # jump to anything
                self.matrices[chord][noteList[chord][index]] \
                                    [noteList[chord][index+1]] += 1
                
                # increment total number of times this interval was updated
                self.matrices[chord][noteList[chord][index]][13] += 1

    def __normalize_matrices(self):
        ''' When this function is called all of the matrices contain the total
            number of times in which some interval i jumped to j. This function
            takes these counts and divides by the number of times i jumps to
            anything. These floats represent the probabilities of jumping from
            one interval to another                                         '''

        for chords in self.matrices:
            for row in self.matrices[chords]:
                if row[13] != 0: # avoid divide by 0 errors by not normalizing
                                 # matrices that do not have anything in them.
                    for interval in range(len(row)-1):
                        row[interval] = float(row[interval])/float(row[13])

    def new_note(self,old_note,chord_note,chord_type):
        ''' New_note takes a note and a chord and using the probability
            matrices, randomly generates the next note. It does this by
            checking the interval between the old note and the chord. It then
            isolates the row of the corresponding interval in the appropiate
            chord class matrix and traverses a the row, adding probabilities
            as it goes, until it reaches a uniformly chosen number between
            0 and 1.                                                        '''

        randomNum = random.random()
        total = 0

        old_note = note.Note(old_note)
        start_interval = self.__find_interval(chord_note, old_note) # find interval
        row = self.matrices[chord_type][start_interval]
        tonic_pitch = pitch.Pitch(chord_note).pitchClass

        for index in range(0,len(row)-1):
            if row[index] + total < randomNum: # traverse list until sum is
                                               # greater than random number
                total += row[index]
            else:
                if index==12: # if interval is rest interval
                    return 12
                else:
                    return (index+tonic_pitch)%12 # return interval of the chord
                    break
    
class improv:
    ''' The improv class creates a rhythm and pitch object and uses as well as
        a music21 stream. It creates the pitch and rhythm objects in the
        initialization method using the provided corpus. Once the main function
        has created an instance of the improv class, it can call the gen method
        with a chord file which will generate a solo in the solo stream. This
        strem is an attribute of the class so it can later be accessed and
        shown through a music reader installed on the user's computer.       '''
        
    solo = stream.Stream()
    pitchMatrix = []
    rhythmMatrix = []

    def __init__(self, directory):
        ''' The initialization function will create instances of the pitch and
            rhythm classes so that they can be later used to generate solos  '''

        mm = tempo.MetronomeMark(number=160) # 160 temp
        inst = instrument.Viola() # Instrument is tenor sax
        self.solo.append(inst)
        self.solo.append(mm)
        self.pitchMatrix = pitches(directory)
        self.rhythmMatrix = rhythm(directory)

    def gen(self,chords):
        ''' This function reads the user's chord file and iterates over all
            chords for all measures and creates notes from the rhythm and
            pitch matrix that will fill the time needed for each measure    '''

        chordfile = open(str(chords)) 
        chord = shlex.split(chordfile.readline()) # parse chord line by line
        chord_tonic = chord[0]
        chord_type = chord[1]
        chord_duration = float(chord[2])

        for rand in range(200): # cycle through pitches and rhythms so we have
                                # random starting point
            length = self.rhythmMatrix.new_note(0)
            pitch = self.pitchMatrix.new_note(0,chord_tonic,chord_type)

        while (len(chord) == 3): # while we have a chord to improvise on
            length = self.rhythmMatrix.new_note(length)
            pitch = self.pitchMatrix.new_note(pitch,chord_tonic,chord_type)

            if pitch == 12: # if pitch is a rest
                nextNote = note.Rest()
            else: # create a music21 object with correct pitch
                nextNote = note.Note(pitch)
            if length == 17: # if rhythm is an eight triplet we must add them
                             # into our piece in groups of three
                nextNote.duration.quarterLength = 1.0/3.0
                self.solo.append(nextNote)
                pitch = self.pitchMatrix.new_note(pitch,chord_tonic,chord_type)
                nextNote = note.Note(pitch)
                nextNote.duration.quarterLength = 1.0/3.0
                self.solo.append(nextNote)
                pitch = self.pitchMatrix.new_note(pitch,chord_tonic,chord_type)
                nextNote = note.Note(pitch)
                nextNote.duration.quarterLength = 1.0/3.0

            elif length == 18: # if rhpitchthm is a sixteenth triplet add them
                               # into our piece in groups of three
                nextNote.duration.quarterLength = 1.0/6.0
                self.solo.append(nextNote)
                pitch = self.pitchMatrix.new_note(pitch,chord_tonic,chord_type)
                nextNote = note.Note(pitch)
                nextNote.duration.quarterLength = 1.0/6.0
                self.solo.append(nextNote)
                pitch = self.pitchMatrix.new_note(pitch,chord_tonic,chord_type)
                nextNote = note.Note(pitch)
                nextNote.duration.quarterLength = 1.0/6.0

            else:
                nextNote.duration.quarterLength = float(length)/4.0

            self.solo.append(nextNote)

            # decrement how much time how chord has left to played
            chord_duration = float(chord_duration) - \
                             float(nextNote.duration.quarterLength)/4.0
            if chord_duration <= 0: # if our chord is finished, 
                chord = shlex.split(chordfile.readline())
                if (len(chord) == 3):
                    chord_tonic = chord[0]
                    chord_type = chord[1]
                    chord_duration = chord[2]

if __name__ == "__main__":
    random.seed() # start by seeding the random number generator

    corpusDirectory = raw_input("Input corpus directory (default 'data/Charts'): ")
    if corpusDirectory == "":
        corpusDirectory = "../data/Charts"
    
    userChords = raw_input("Input chord file (default 'data/user_chords'): ")
    if userChords == "":
        userChords = "../data/user_chords"

    improvisation = improv(corpusDirectory)
    improvisation.gen(userChords)

    improvisation.solo.show()
