# -*- coding: utf-8 -*-

import codecs
import re
import numpy as np
import os

from lyrics import Lyrics

def read_lyrics(lyrics_dir='lyrics', artist=None, album=None, print_stats=False):
    '''
    Read lyrics and compute the average rhyme length (riimikerroin) for each
    artist.

    Input:
        lyrics_dir  Path to the directory containing the lyrics.
        artist      Name of the artist directory under lyrics_dir (if this is
                    not provided, all artists are analyzed).
        album       Name of the album directory under lyrics_dir/artist/
        print_stats Whether we print summary statistics for each individual
                    song.
    '''
    if artist is not None:
        artists = [artist]
    else:
        artists = os.listdir(lyrics_dir)
    artist_scores = []
    song_scores = []
    song_names = []
    uniq_words = []
    for a in artists:
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
                l = Lyrics(file_name, print_stats=print_stats)
                rl = l.get_avg_rhyme_length()
                rls.append(rl)
                song_scores.append(rl)
                song_names.append(file_name)
                album_rls.append(rl)
                all_words += l.text.split()
            # Print stats for the album
            #print "%s - %s: %.3f" % (a, al, np.mean(np.array(album_rls)))

        # Compute the number of unique words the artist has used
        n_words = len(all_words)
        min_w = 9000
        if n_words >= min_w:
            uniq_words.append(len(set(all_words[:min_w])))
            #print "%.2f\t%d\t%s" % (np.mean(np.array(rls)), n_uniq_words, a)
        else:
            uniq_words.append(-1)
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

    print "\nBest artists:"
    for i in range(len(artist_scores)):
        rx = re.compile(u'_')
        name = rx.sub(' ', artists[i])
        print '%.3f\t%s' % (artist_scores[i], name)
        #if uniq_words[i] != -1:
        #    print '%.3f\t%s (%d unique words)' % (artist_scores[i], name, uniq_words[i])
        #else:
        #    print '%.3f\t%s (not enough lyrics to compute unique words)' % (artist_scores[i], name)

    print "\nBest songs:"
    song_scores = np.array(song_scores)
    song_names = np.array(song_names)
    song_names = song_names[np.argsort(song_scores)[::-1]]
    song_scores = sorted(song_scores)[::-1]
    for i in range(min(25,len(song_scores))):
        rx = re.compile(u'_')
        name = rx.sub(' ', song_names[i])
        print '%.3f\t%s' % (song_scores[i], name)

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
    # Analyze lyrics of all available artists
    read_lyrics(print_stats=False)
    # Analyze lyrics of Paleface
    #read_lyrics(artist='Paleface', print_stats=True)

if __name__ == '__main__':
    main()
