import librosa


def extract_volume_tags(file, num_tags=500):
    y, sr = librosa.load(file)

    frame_length = len(y) // num_tags
    if frame_length < 1:
        frame_length = 1

    waveform_data = []
    for i in range(0, len(y), frame_length):
        chunk = y[i : i + frame_length]
        if len(chunk) >= 1
