import glob
#import os
import wave

fil = raw_input("Qual o diretorio ?")
#files = os.listdir(fil)
files = glob.glob(fil)

infiles = files
outfile = "merged.wav"

data= []
for infile in infiles:
    w = wave.open(infile, 'rb')
    data.append([w.getparams(), w.readframes(w.getnframes())])
    w.close()

output = wave.open(outfile, 'wb')
output.setparams(data[0][0])
output.writeframes(data[0][1])
output.writeframes(data[1][1])
output.close()