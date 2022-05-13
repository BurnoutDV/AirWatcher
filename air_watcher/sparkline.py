
import numpy
import wave
from time import time_ns
"""
import sounddevice
devices = sounddevice.query_devices()
sample_rate = 48000

thing = sounddevice.rec(
    int(0.1 * sample_rate),
    device="HDA Intel PCH: CX8070 Analog (hw:0,0)",
    samplerate=sample_rate,
    blocking=True,
    channels=1,
    dtype='float64')

recording = thing
magnitude = numpy.abs(numpy.fft.rfft(recording[:, 0], n=sample_rate))
print(numpy.mean(magnitude[20:2000]))
"""

import numpy
import wave


def audio_sparklines(audio_mono_file: str, chars=32, skip=1, low_pass=None, high_pass=None) -> str:
    """
    Creates a simple representation of a given audio file by a 8 bit representation and 32 chars (by default)
    Inspired by this: https://melatonin.dev/blog/audio-sparklines/

    :param str audio_mono_file: path to a wave file, mono NOT stereo
    :param int chars: number of characters representing the line
    :param int skip: number of frames that get skipped to speed up processing
    :param int low_pass: lower limit for frequency in Hz
    :param int high_pass: higher limit for frequency in Hz
    """

    # sanitation of input, not sure if i am actually liable to do this
    sparkslrr = (' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█')

    if not isinstance(chars, int) or chars < 4:
        chars = 4
    if low_pass and high_pass:
        if low_pass < 20 or low_pass > 8000:
            low_pass = 20
        if high_pass < 21 or high_pass > 8000:
            high_pass = 8000
        if high_pass < low_pass:
            low_pass = low_pass + high_pass
            high_pass = low_pass - high_pass
            low_pass = low_pass - high_pass
    else:
        low_pass = None
        high_pass = None

    # input of file using wave library - TODO: use something more universal
    ifile = wave.open(audio_mono_file)
    sample_rate = ifile.getframerate()
    audio = ifile.readframes(ifile.getnframes())
    audio_int16 = numpy.frombuffer(audio, dtype=numpy.int16)
    audio_float32 = audio_int16.astype(numpy.float32)

    # fancy math i cannot fully comprehend, per https://stackoverflow.com/a/62298670
    max_int16 = 2**15
    audio_norm = audio_float32 / max_int16
    # parting the big array in equal sized parts

    n = len(audio_norm)
    magnis = {}
    parts = int(n/chars)
    for i in range(chars-1):
        start = i * parts
        stop = (i+1) * parts
        if stop > n:
            stop = n-1
        # using a fast fourier transformation of the signal, university math class is far in the past, don't crucify me
        magnis[i] = numpy.abs(numpy.fft.rfft(audio_norm[start:stop:skip], n=sample_rate))

    # apply high & low pass if they are actually set, not sure why exactly this works with this numpy array
    if low_pass and high_pass:
        ranging = {i: numpy.mean(magnis[i][low_pass:high_pass]) for i in range(chars-1)}
    else:
        ranging = {i: numpy.mean(magnis[i]) for i in range(chars-1)}
    # dumping down the signal to an equal scale from 0 to 7, might be wise to use a logarithmic scale?
    maxi = max(ranging.values())
    steps = maxi/8
    line = [int(x/steps) for x in ranging.values()]

    # creating the actual str line
    spark_line = ""
    for char in line:
        spark_line += sparkslrr[char]
    return spark_line


if __name__ == "__main__":
    epoch = time_ns()
    print(audio_sparklines("../rose_mono.wav", skip=1))
    print(f"Elapsed: {int((time_ns()-epoch)/1000000)}ms")