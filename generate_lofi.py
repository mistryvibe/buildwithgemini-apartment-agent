import math
import numpy as np
import wave

def generate_lofi_beat(output_filename="lofi_beat.wav", duration_sec=40, sample_rate=44100):
    num_samples = duration_sec * sample_rate
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    
    bpm = 85
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4
    
    # 1. Chords (Cmaj7 -> Am7 -> Dm7 -> G7)
    # Frequencies (Hz)
    chords = [
        [261.63, 329.63, 392.00, 493.88], # Cmaj7
        [220.00, 261.63, 329.63, 392.00], # Am7
        [293.66, 349.23, 440.00, 523.25], # Dm7
        [196.00, 246.94, 293.66, 349.23], # G7
    ]
    
    audio = np.zeros(num_samples)
    
    # Synthesize electric piano / warm synth chords
    for i in range(num_samples):
        sec = t[i]
        bar_idx = int(sec / bar_sec) % len(chords)
        chord_freqs = chords[bar_idx]
        
        # Envelope within each bar (soft attack, decay)
        bar_t = (sec % bar_sec)
        env = np.exp(-1.2 * bar_t) * (1 - np.exp(-15 * bar_t))
        
        chord_wave = 0.0
        for f in chord_freqs:
            # Warm sine + slight 2nd harmonic for electric piano tone
            chord_wave += 0.6 * np.sin(2 * np.pi * f * sec) + 0.25 * np.sin(4 * np.pi * f * sec)
        
        audio[i] += chord_wave * env * 0.25
        
    # 2. Bassline (Root notes of chords)
    bass_freqs = [130.81, 110.00, 146.83, 98.00] # C3, A2, D3, G2
    for i in range(num_samples):
        sec = t[i]
        bar_idx = int(sec / bar_sec) % len(bass_freqs)
        bf = bass_freqs[bar_idx]
        beat_t = (sec % beat_sec)
        bass_env = np.exp(-3.0 * beat_t)
        # Deep warm bass
        audio[i] += (0.45 * np.sin(2 * np.pi * (bf/2) * sec) + 0.2 * np.sin(2 * np.pi * bf * sec)) * bass_env * 0.35

    # 3. Drum beat (Upbeat Lo-Fi Hip Hop: Kick on 1 & 3, Snare on 2 & 4, Hi-hats on 8ths)
    for i in range(num_samples):
        sec = t[i]
        beat_in_bar = (sec % bar_sec) / beat_sec
        beat_frac = beat_in_bar % 1.0
        beat_int = int(beat_in_bar)
        
        # Kick (Low frequency drop)
        if (beat_int == 0 or beat_int == 2 or (beat_int == 2 and beat_frac >= 0.75)) and beat_frac < 0.15:
            kick_env = np.exp(-25.0 * beat_frac)
            kick_freq = 110.0 * np.exp(-15.0 * beat_frac)
            audio[i] += np.sin(2 * np.pi * kick_freq * sec) * kick_env * 0.45
            
        # Snare / Rimshot (Noise + body)
        if (beat_int == 1 or beat_int == 3) and beat_frac < 0.2:
            snare_env = np.exp(-20.0 * beat_frac)
            noise = np.random.normal(0, 0.3)
            snare_body = np.sin(2 * np.pi * 180 * sec) * 0.3
            audio[i] += (noise + snare_body) * snare_env * 0.28
            
        # Hi-hats (Short noise burst on 8th notes)
        eighth_frac = (sec % (beat_sec / 2)) / (beat_sec / 2)
        if eighth_frac < 0.08:
            hat_env = np.exp(-50.0 * eighth_frac)
            hat_noise = np.random.normal(0, 0.2)
            audio[i] += hat_noise * hat_env * 0.15

    # 4. Vinyl crackle / tape hiss warmth
    crackle = np.random.normal(0, 0.012, num_samples)
    audio += crackle

    # Normalize audio to prevent clipping
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.85

    # Convert to 16-bit PCM WAV
    audio_int16 = (audio * 32767).astype(np.int16)
    
    with wave.open(output_filename, "w") as wf:
        wf.setnchannels(1) # Mono
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
        
    print(f"Generated lo-fi beat track: {output_filename} ({duration_sec}s)")

if __name__ == "__main__":
    generate_lofi_beat()
