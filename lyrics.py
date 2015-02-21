# -*- coding: utf-8 -*-

import codecs
import re
import numpy as np
import os

import phonetics as ph

class Lyrics:
    '''
    This class is used to store and preprocess rap lyrics and calculate
    statistics like average rhyme length out of the lyrics.
    '''

    def __init__(self, filename=None, print_stats=False, text=None, 
                 language='fi', lookback=10):
        '''
        Lyrics can be read from the file (default) or passed directly
        to this constructor.
        '''
        self.text_raw = None
        # How many previous words are checked for a rhyme.
        self.lookback = lookback
        if filename is not None:
            self.filename = filename
            f = codecs.open(filename, 'r', 'utf8')
            self.text_raw = f.read()
            f.close()
        elif text is not None:
            self.text_raw = text
            self.filename = 'No filename'
        self.language = language

        if self.text_raw is not None:
            cleaning_ok = self.clean_text(self.text_raw)
            self.compute_vowel_representation()
            self.avg_rhyme_length, self.longest_rhyme = self.rhyme_stats()

            if print_stats:
                #self.print_song_stats_compact()
                self.print_song_stats()

    def clean_text(self, text):
        '''
        Preprocess text by removing unwanted characters and duplicate rows.
        '''
        if self.language == 'fi':
            self.text = text.lower()
            # Replace all but word characters and newlines by spaces
            rx = re.compile(u'[^\wåäö\n]+')
        else: # English
            self.text = text
            # For English we need to keep apostrophes since they affect the 
            # pronunciation
            rx = re.compile(u"[^\wåÅäÄöÖéÉ'’\.\?!\n]+")

        self.text = rx.sub(' ', self.text)
        # If there are more than 2 consecutive newlines, remove some of them
        # (just to make the cleaned text look prettier)
        self.text = re.sub('\n\n+', '\n\n', self.text)
        # Remove duplicate rows
        self.lines = self.text.split('\n')

        uniq_lines = set()
        new_text = ''
        for l in self.lines:
            l = l.strip()
            if len(l) > 0 and l in uniq_lines:
                continue
            # Remove lines that are within brackets/parenthesis
            if len(l) >= 2 and ((l[0]=='[' and l[-1]==']') or (l[0]=='(' and l[-1]==')')):
                continue
            uniq_lines.add(l)
            if self.language == 'fi':
                new_text += l + '\n'
            else: # English
                # Add '.' to the end of line since otherwise the lines might be
                # too long so that espeak won't transcribe the whole line
                new_text += l + '.\n'

        self.text = new_text

    def compute_vowel_representation(self):
        '''
        Compute a representation of the lyrics where only vowels are preserved.
        '''
        self.vow = [] # Lyrics with all but vowels removed
        self.vow_idxs = [] # Indices of the vowels in self.text list
        self.word_ends = [] # Indices of the last characters of each word
        self.words = [] # List of words in the lyrics
        self.line_idxs = []

        if len(self.language) >= 2 and self.language[:2] == 'en':
            self.text_orig = self.text
            self.text = ph.get_phonetic_transcription(self.text, output_fname=self.filename+'.ipa')
            self.word_ends_orig = []
            self.words_orig = []

        prev_space_idx = -1 # Index of the previous space char
        line_idx = 0 # Line index of the current character
        # Go through the lyrics char by char
        for i in range(len(self.text)):
            self.line_idxs.append(line_idx)
            c = self.text[i]
            c = ph.map_vow(c, self.language)
            if ph.is_vow(c, self.language):
                # Ignore double vowels
                # (in English this applies probably only to 'aa' as in 'bath'
                # which rhymes with 'trap' that has only 'a')
                if i > 0 and self.text[i-1] == c:
                    # Index of a double vowel points to the latter occurrence
                    self.vow_idxs[-1] = i
                    continue
                # TODO Diftongs should not be split (i.e. "price" should
                # not rhyme with "trap kit"). This has been fixed in BattleBot
                self.vow.append(c)
                self.vow_idxs.append(i)
            elif ph.is_space(c):
                if c in '\n':
                    line_idx += 1
                elif c in '.!?' and i < len(self.text)-1 and self.text[i+1] != '\n':
                    line_idx += 1
                # If previous char was not a space, we've encountered word end
                if len(self.vow) > 0 and not ph.is_space(self.text[i-1]):
                    # Put together the new word. Potential consonants in the 
                    # end are ignored
                    new_word = self.text[prev_space_idx+1:self.vow_idxs[-1]+1]
                    # Check that the new word contains at least one vowel
                    no_vowels = True
                    for c2 in new_word:
                        if ph.is_vow(c2, self.language):
                            no_vowels = False
                            break
                    if no_vowels:
                        prev_space_idx = i
                        continue
                    self.word_ends.append(len(self.vow)-1)
                    self.words.append(new_word)
                prev_space_idx = i

        if len(self.language) >= 2 and self.language[:2] == 'en':
            self.lines_orig = self.text_orig.split('\n')

    def rhyme_length(self, wpos2):
        '''
        Length of rhyme (in vowels). The latter part of the rhyme ends with 
        word self.words[wpos2].

        Input:
            wpos2       Word index of the end of the rhyme.
        '''
        max_length = 0
        max_wpos1 = None
        wpos1 = max(0,wpos2-self.lookback)
        while wpos1 < wpos2:
            rl = self.rhyme_length_fixed(wpos1, wpos2)
            if rl > max_length:
                max_length = rl
                max_wpos1 = wpos1
            wpos1 += 1
        return max_length, max_wpos1

    def rhyme_length_fixed(self, wpos1, wpos2):
        '''
        Length of rhyme (in vowels). The first part of the rhyme ends with 
        self.words[wpos1] and the latter part with word self.words[wpos2].

        Input:
            wpos1       Word index of the last word in the first part of the rhyme.
            wpos2       Word index of the end of the rhyme.
        '''
        if wpos1 < 0: # Don't wrap
            return 0
        elif self.words[wpos1] == self.words[wpos2]:
            return 0
        # Indices in the vowel list
        p1 = self.word_ends[wpos1]
        p2 = self.word_ends[wpos2]
        l = 0
        while self.vow[p1-l] == self.vow[p2-l]:
            # Make sure that exactly same words are not used
            if wpos1 > 0 and p1-l <= self.word_ends[wpos1-1] and wpos2 > 0 and p2-l <= self.word_ends[wpos2-1]:
                # Get the first and last character indices of the words surrounding the vowels at p1-l and p2-l
                prev_s1 = self.vow_idxs[p1-l]
                while prev_s1 > 0 and not ph.is_space(self.text[prev_s1-1]):
                    prev_s1 -= 1
                prev_s2 = self.vow_idxs[p2-l]
                while prev_s2 > 0 and not ph.is_space(self.text[prev_s2-1]):
                    prev_s2 -= 1
                next_s1 = self.vow_idxs[p1-l]
                while next_s1 < len(self.text)-1 and not ph.is_space(self.text[next_s1+1]):
                    next_s1 += 1
                next_s2 = self.vow_idxs[p2-l]
                while next_s2 < len(self.text)-1 and not ph.is_space(self.text[next_s2+1]):
                    next_s2 += 1
                if next_s1-prev_s1 == next_s2-prev_s2 and self.text[prev_s1:next_s1+1] ==  self.text[prev_s2:next_s2+1]:
                    break

            l += 1
            if p1-l < 0 or p2-l <= p1:
                break
        # Ignore rhymes with length 1
        if l == 1:
            l = 0
        return l

    def rhyme_stats(self):
        '''
        Compute the average rhyme length of the song and the longest rhyme.

        Output:
            Average rhyme length (float)
            Longest rhyme which is a 3-tuple with: 
                (length, word index of the first part of the rhyme,
                         word index of the latter part of the rhyme)
        '''
        # Rhyme length of each word
        rls = []
        # Keep track of the longest rhyme
        max_rhyme = (0,None,None)
        for wpos2 in range(1,len(self.word_ends)):
            (rl, wpos1) = self.rhyme_length(wpos2)
            rls.append(rl)
            if rl > max_rhyme[0]:
                max_rhyme = (rl, wpos1, wpos2)
        rls = np.array(rls)
        # Average rhyme length of the song
        if len(rls) > 0:
            avg_rl = np.mean(rls)
        else:
            avg_rl = 0
        return avg_rl, max_rhyme

    def get_avg_rhyme_length(self):
        return self.avg_rhyme_length

    def print_song_stats(self):
        print '------------------------------------------'
        print "%s\n" % self.filename

        print "Avg rhyme length: %.3f\n" % self.avg_rhyme_length

        self.print_rhyme(self.longest_rhyme)
        print
        #print '------------------------------------------'

    def print_song_stats_compact(self):
        print "%.3f  %s" % (self.avg_rhyme_length, self.filename)

    def print_rhyme(self, rhyme_tuple):
        print self.get_rhyme_str(rhyme_tuple)

    def get_rhyme_str(self, rhyme_tuple):
        '''
        Construct a string of a given rhyme tuple.
        '''
        ret = ''
        rl, wpos1, wpos2 = rhyme_tuple
        if wpos1 is None or wpos2 is None:
            return ''
        p2 = self.vow_idxs[self.word_ends[wpos2]]
        p2_orig = p2
        # Find the ending of the last word
        while not ph.is_space(self.text[p2]):
            p2 += 1
        p0 = self.vow_idxs[self.word_ends[wpos1]-rl]
        p0_orig = p0
        # Find the beginning of the line
        while self.text[p0] != '\n' and p0 > 0:
            p0 -= 1

        cap_line = ''
        rw1, rw2 = self.get_rhyming_vowels(rhyme_tuple)
        for i in range(p0,p2+1):
            if self.language == 'fi':
                if i in rw1 or i in rw2:
                    cap_line += self.text[i].capitalize()
                else:
                    cap_line += self.text[i]
            else:
                if i == min(rw1) or i == min(rw2):
                    cap_line += ' | ' + self.text[i]
                elif i == max(rw1) or i == max(rw2):
                    cap_line += self.text[i] + '|'
                else:
                    cap_line += self.text[i]
        ret += "Longest rhyme (l=%d): %s\n" % (rl, cap_line)
        if self.language != 'fi':
            # Get the corresponding lines from the original lyrics
            line_beg = self.line_idxs[p0]
            line_end = self.line_idxs[p2]
            for i in range(line_beg, line_end+1):
                if i < len(self.lines_orig):
                    ret += self.lines_orig[i] + '\n'
        return ret

    def get_longest_rhyme(self):
        rhyme_str = self.get_rhyme_str(self.longest_rhyme)
        rhyme_str += self.filename + '\n'
        return self.longest_rhyme[0], rhyme_str

    def get_rhyming_vowels(self, rhyme_tuple):
        '''
        Return the indices of the rhyming vowels of the longest rhyme.

        Output:
            Tuple with the indices of the first part and the second part of
            the rhyme separately.
        '''
        rl, wpos1, wpos2 = rhyme_tuple
        if wpos1 is None or wpos2 is None:
            return ([-1],[-1])

        # The first part of the rhyme
        rhyme_idxs1 = [] # Indices of the rhyming vowels
        n_caps = 0
        p = self.vow_idxs[self.word_ends[wpos1]]
        while n_caps < rl:
            if ph.is_vow(self.text[p], self.language):
                rhyme_idxs1.append(p)
                # Increase the counter only if the vowel is not a double vowel
                if self.text[p] != self.text[p+1]:
                    n_caps += 1
            p -= 1

        # The second part of the rhyme
        rhyme_idxs2 = [] # Indices of the rhyming vowels
        n_caps = 0
        p = self.vow_idxs[self.word_ends[wpos2]]
        p_last = p
        while n_caps < rl:
            if ph.is_vow(self.text[p], self.language):
                rhyme_idxs2.append(p)
                # Increase the counter only if the vowel is not a double vowel.
                # The last vowel must be always counted.
                if p == p_last or self.text[p] != self.text[p+1]:
                    n_caps += 1
            p -= 1

        return (rhyme_idxs1, rhyme_idxs2)
