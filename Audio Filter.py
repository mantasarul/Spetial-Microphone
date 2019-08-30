import sys
import math
import wave
import struct
import curses
import pyaudio
import numpy as np
import matplotlib.pyplot as plt

stdscr = curses.initscr()
stdscr.nodelay(True)
curses.noecho()
curses.cbreak()

pa = pyaudio.PyAudio()

MODE = sys.argv[1]

CHUNK = 1

CHANNELS = 2

WIDTH = 2

SAMPLE_RATE = 44100

if MODE != '-p' and MODE != '--playback':
    try:
        NTH_ITERATION = int(sys.argv[3])
    except (ValueError, IndexError):
        print('The second argument has to be a number')
        sys.exit()

def main():    
    if MODE == '--file' or MODE == '-f':
        file_mode()
    elif MODE == '--live' or MODE == '-l':
        live_mode()
    elif MODE == '--playback' or MODE == '-p':
        playback_mode()
    else:
        print('Please either choose file-mode, live-mode or playback-mode with the first argument')

def file_mode():    
    (waveform, stream) = readin(sys.argv[4])   
    stdscr.addstr('Now noise-cancelling the file')
    decibel_levels = []
    total_original = []
    total_inverted = []
    total_difference = []   
    iteration = 0

    
    ratio = 1.0

  
    active = True

   
    original = waveform.readframes(CHUNK)
    while original != b'':
        try:
            
            pressed_key = stdscr.getch()

          
            if pressed_key == 111:
                active = not active
                
                if not active:
                    ratio = 2.0
                else:
                    ratio = 1.0
            
            elif pressed_key == 43:
                ratio += 0.01
            
            elif pressed_key == 45:
                ratio -= 0.01
            
            elif pressed_key == 120:
                break

            
            inverted = invert(original)

           
            if active:
                mix = mix_samples(original, inverted, ratio)
                stream.write(mix)
          
            else:
                stream.write(original)

            
            if iteration % NTH_ITERATION == 0:
               
                stdscr.clear()
               
                difference = calculate_difference(original, inverted)
               
                stdscr.addstr('Difference (in dB): {}\n'.format(difference))
                
                decibel_levels.append(difference)
               
                int_original, int_inverted, int_difference = calculate_wave(original, inverted, ratio)
                total_original.append(int_original)
                total_inverted.append(int_inverted)
                total_difference.append(int_difference)

           
            original = waveform.readframes(CHUNK)

         
            iteration += 1

        except (KeyboardInterrupt, SystemExit):
            break

   
    stream.stop_stream()
    stream.close()

   
    print('Finished noise-cancelling the file')

   
   """ if sys.argv[2] == '--decibel' or sys.argv[2] == '-db':
    
        plot_results(decibel_levels, NTH_ITERATION)
    elif sys.argv[2] == '--waves' or sys.argv[2] == '-wv':
        plot_wave_results(total_original, total_inverted, total_difference, NTH_ITERATION)
"""
    
    curses.endwin()

    
    pa.terminate()
    sys.exit()


def live_mode():
    
    stdscr.addstr('Now noise-cancelling live')

    
    stream = pa.open(
        format=pa.get_format_from_width(WIDTH),
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        frames_per_buffer=CHUNK,
        input=True,
        output=True
    )

    
    decibel_levels = []

    
    total_original = []
    total_inverted = []
    total_difference = []

   
    active = True

   
    try:
        for i in range(0, int(SAMPLE_RATE / CHUNK * sys.maxunicode)):

            pressed_key = stdscr.getch()

          
            if pressed_key == 111:
                active = not active

           
            if pressed_key == 120:
                break

            
            original = stream.read(CHUNK)

            
            inverted = invert(original)

            stream.write(inverted, CHUNK)

            
            if i % NTH_ITERATION == 0:
                
                stdscr.clear()
                
                difference = calculate_difference(original, inverted)
                
                stdscr.addstr('Difference (in dB): {}'.format(difference))
                
                decibel_levels.append(difference)
                
                int_original, int_inverted, int_difference = calculate_wave(original, inverted)
                total_original.append(int_original)
                total_inverted.append(int_inverted)
                total_difference.append(int_difference)

    except (KeyboardInterrupt, SystemExit):
        
        print('Finished noise-cancelling the file')

        
        if sys.argv[2] == '--decibel' or sys.argv[2] == '-db':
            plot_results(decibel_levels, NTH_ITERATION)
        elif sys.argv[2] == '--waves' or sys.argv[2] == '-wv':
            plot_wave_results(total_original, total_inverted, total_difference, NTH_ITERATION)

       
        curses.endwin()

       
        stream.stop_stream()
        stream.close()
        pa.terminate()
        sys.exit()


def playback_mode():
    
    (waveform, stream) = readin(sys.argv[2])

  
    print('Now playing back the file')

  
    original = waveform.readframes(CHUNK)
    while original != b'':
        try:
           
            stream.write(original)

           
            original = waveform.readframes(CHUNK)
        except (KeyboardInterrupt, SystemExit):
            break

  
    stream.stop_stream()
    stream.close()

  
    print('Finished playing back the file')


    pa.terminate()
    sys.exit()


def readin(file):
   
    try:
        waveform = wave.open(file, 'r')
    except wave.Error:
        print('The program can only process wave audio files (.wav)')
        sys.exit()
    except FileNotFoundError:
        print('The chosen file does not exist')
        sys.exit()

    
    stream = pa.open(
        format=pa.get_format_from_width(waveform.getsampwidth()),
        channels=waveform.getnchannels(),
        rate=waveform.getframerate(),
        output=True
    )

    
    return waveform, stream


def invert(data):
    
    intwave = np.fromstring(data, np.int32)
   
    intwave = np.invert(intwave)
   
    inverted = np.frombuffer(intwave, np.byte)
   
    return inverted


def mix_samples(sample_1, sample_2, ratio):
    
    (ratio_1, ratio_2) = get_ratios(ratio)
    
    intwave_sample_1 = np.fromstring(sample_1, np.int16)
    intwave_sample_2 = np.fromstring(sample_2, np.int16)
    
    intwave_mix = (intwave_sample_1 * ratio_1 + intwave_sample_2 * ratio_2).astype(np.int16)
   
    mix = np.frombuffer(intwave_mix, np.byte)
    return mix


def get_ratios(ratio):
    
    ratio = float(ratio)
    ratio_1 = ratio / 2
    ratio_2 = (2 - ratio) / 2
    return ratio_1, ratio_2


def calculate_decibel(data):
   

    count = len(data) / 2
    form = "%dh" % count
    shorts = struct.unpack(form, data)
    sum_squares = 0.0
    for sample in shorts:
        n = sample * (1.0 / 32768)
        sum_squares += n * n
    rms = math.sqrt(sum_squares / count) + 0.0001
    db = 20 * math.log10(rms)
    return db


def calculate_difference(data_1, data_2):
   

    difference = calculate_decibel(data_1) - calculate_decibel(data_2)
    return difference


def calculate_wave(original, inverted, ratio):
    

   
    (ratio_1, ratio_2) = get_ratios(ratio)
 
    int_original = np.fromstring(original, np.int16)[0] * ratio_1
    int_inverted = np.fromstring(inverted, np.int16)[0] * ratio_2
    
    int_difference = (int_original + int_inverted)

    return int_original, int_inverted, int_difference


def plot_results(data, nth_iteration):
   
  
    plt.plot(data[10:])

   
    plt.xlabel('Time (every {}th {} byte)'.format(nth_iteration, CHUNK))
    plt.ylabel('Volume level difference (in dB)')

   
    plt.suptitle('Difference - Median (in dB): {}'.format(np.round(np.fabs(np.median(data)), decimals=5)), fontsize=14)


    plt.show()


def plot_wave_results(total_original, total_inverted, total_difference, nth_iteration):
   
    plt.plot(total_original, 'b')
    plt.plot(total_inverted, 'r')
    plt.plot(total_difference, 'g')

    
    plt.xlabel('Time (per {}th {} byte chunk)'.format(nth_iteration, CHUNK))
    plt.ylabel('Amplitude (integer representation of each {} byte chunk)'.format(nth_iteration, CHUNK))

   
    plt.suptitle('Waves: original (blue), inverted (red), output (green)', fontsize=14)

   
    plt.show()



main()