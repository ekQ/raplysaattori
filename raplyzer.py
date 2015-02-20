# -*- coding: utf-8 -*-
import codecs
import re
import numpy as np
import os
import heapq
import datetime as dt
import json

from lyrics import Lyrics

def read_lyrics(lyrics_dir='lyrics_en', artist=None, album=None, 
                print_stats=False, language='en-us', lookback=15):
    '''
    Read lyrics and compute Rhyme factor (riimikerroin) for each
    artist.

    Input:
        lyrics_dir  Path to the directory containing the lyrics.
        artist      Name of the artist directory under lyrics_dir (if this is
                    not provided, all artists are analyzed).
        album       Name of the album directory under lyrics_dir/artist/
        print_stats Whether we print summary statistics for each individual
                    song.
        language    Use either Finnish (fi), American English (en-us), 
                    or English (en).
        lookback    How many previous words are checked for rhymes. For
                    Finnish I've used 10 and for English 15.
    '''
    if artist is not None:
        artists = [artist]
    else:
        artists = os.listdir(lyrics_dir)
    artist_scores = []
    song_scores = []
    song_names = []
    uniq_words = []
    longest_rhymes = []
    max_rhymes = 5
    for a in artists:
        print "Analyzing artist: %s" % a
        rls = []
        all_words = []
        if album is not None:
            albums = [album]
        else:
            albums = os.listdir(lyrics_dir+'/'+a)
            albums = sort_albums_by_year(albums)
        for al in albums:
            album_rls = []
            songs = os.listdir(lyrics_dir+'/'+a+'/'+al)
            # Only the .txt files
            songs = [s for s in songs if len(s)>=4 and s[-4:]=='.txt']
            for song in songs:
                file_name = lyrics_dir+'/'+a+'/'+al+'/'+song
                l = Lyrics(file_name, print_stats=print_stats, 
                           language=language, lookback=lookback)
                rl = l.get_avg_rhyme_length()
                rls.append(rl)
                song_scores.append(rl)
                song_names.append(file_name)
                album_rls.append(rl)
                if len(longest_rhymes) < max_rhymes:
                    heapq.heappush(longest_rhymes, l.get_longest_rhyme())
                else:
                    heapq.heappushpop(longest_rhymes, l.get_longest_rhyme())

                if language == 'fi':
                    all_words += l.text.split()
                else:
                    text = l.text_orig.lower()
                    rx = re.compile(u'[^\wåäö]+')
                    text = rx.sub(' ', text)
                    all_words += text.split()
            # Print stats for the album
            #print "%s - %s: %.3f" % (a, al, np.mean(np.array(album_rls)))
            #print "%.5f" % (np.mean(np.array(album_rls)))

        # Compute the number of unique words the artist has used
        n_words = len(all_words)
        min_w = 20000
        if n_words >= min_w:
            n_uniq_words = len(set(all_words[:min_w]))
            uniq_words.append(n_uniq_words)
        else:
            uniq_words.append(-n_words)
        mean_rl = np.mean(np.array(rls))
        artist_scores.append(mean_rl)

    # Sort the artists based on their avg rhyme lengths
    artist_scores = np.array(artist_scores)
    artists = np.array(artists)
    uniq_words = np.array(uniq_words)
    order = np.argsort(artist_scores)[::-1]
    artists = artists[order]
    uniq_words = uniq_words[order]
    artist_scores = artist_scores[order]

    print "\nBest rhymes"
    while len(longest_rhymes) > 0:
        l, rhyme = heapq.heappop(longest_rhymes)
        print rhyme

    print "\nBest songs:"
    song_scores = np.array(song_scores)
    song_names = np.array(song_names)
    song_names = song_names[np.argsort(song_scores)[::-1]]
    song_scores = sorted(song_scores)[::-1]
    for i in range(min(10,len(song_scores))):
        print '%.3f\t%s' % (song_scores[i], song_names[i])

    print "\nBest artists:"
    for i in range(len(artist_scores)):
        rx = re.compile(u'_')
        name = rx.sub(' ', artists[i])
        print '%d.\t%.3f\t%s' % (i+1, artist_scores[i], name)

def sort_albums_by_year(albums):
    years = []
    for a in albums:
        m = re.match('.+y(\d\d\d\d)y$', a)
        if m:
            years.append(int(m.group(1)))
        else:
            years.append(0)
    years = np.array(years)
    albums = np.array(albums)
    albums = list(albums[np.argsort(years)])
    return albums

def main():
    # Analyze lyrics of all available artists (English)
    read_lyrics(lyrics_dir='lyrics_en', language='en-us', lookback=15)
    # Analyze lyrics of Paleface (English)
    #read_lyrics(lyrics_dir='lyrics_en', artist='Paleface', print_stats=True, language='en-us', lookback=15)


    # Analyze lyrics of all available artists (Finnish)
    #read_lyrics(lyrics_dir='lyrics', language='fi', lookback=10)
    # Analyze lyrics of Paleface (Finnish)
    #read_lyrics(lyrics_dir='lyrics', artist='Paleface', language='fi', lookback=10)

if __name__ == '__main__':
    main()
