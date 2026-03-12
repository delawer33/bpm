import librosa
import numpy as np


def extract_volume_tags(file, num_tags=300):
    y, _ = librosa.load(file, sr=22050, mono=True)

    frame_length = max(1, len(y) // num_tags)

    usable = (len(y) // frame_length) * frame_length
    y = y[:usable]

    chunks = y.reshape(-1, frame_length)

    rms = np.sqrt(np.mean(chunks**2, axis=1))

    rms = rms**0.5
    p = np.percentile(rms, 80)
    rms = np.clip(rms / p, 0, 1)
    return rms


def plot_helper():
    import matplotlib.pyplot as plt

    # t = extract_volume_tags("./looperman-a-0807567-0024487-4-the-paper.mp3")
    # t = extract_volume_tags("./6.3.25.mp3")
    t = extract_volume_tags("./Keepin-It-Real--12-Free--Rylo-Rodriguez-Type-Beat.mp3")
    wave1 = t
    wave2 = np.array(t)
    fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    ax[0].bar(range(len(wave1)), wave1)

    ax[1].bar(range(len(wave2)), 2 * wave2, bottom=-wave2)

    plt.show()


if __name__ == "__main__":
    plot_helper()
    pass
