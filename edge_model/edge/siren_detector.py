"""
Northern Blades V5.5 — Acoustic Siren Detector
================================================
Edge-side script that listens via an I2S microphone for emergency
vehicle siren frequencies (1200–1500 Hz) and publishes a detection
event to the MQTT broker.

Uses Doppler volume-gradient analysis:
    - "escalating" amplitude = siren approaching.
    - "stable"     amplitude = siren stationary nearby.
    - "fading"     amplitude = siren moving away.

This is the GPS-failsafe:  if the V2X app loses cellular signal,
the acoustic detector provides a last-resort emergency override.

Dependencies: numpy, paho-mqtt, (pyaudio or sounddevice for live mic)
For the hackathon demo, this script can also operate on pre-recorded
WAV files by setting AUDIO_SOURCE to a file path.
"""

import numpy as np
import json
import time
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[SIREN %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────

# MQTT
BROKER = os.environ.get("NB_MQTT_BROKER", "localhost")
PORT = int(os.environ.get("NB_MQTT_PORT", 1883))
TOPIC = "v2x/siren"

# Audio
SAMPLE_RATE = 16000          # Hz
CHUNK_DURATION = 0.5         # seconds per analysis window
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

# Siren band (Hz)
SIREN_LOW = 1200
SIREN_HIGH = 1500

# Detection thresholds
ENERGY_THRESHOLD = 0.3       # Minimum normalized energy in siren band
CONFIDENCE_THRESHOLD = 0.70  # Minimum confidence to report

# Volume trend analysis
TREND_WINDOW = 6             # Number of recent energy readings to track
ESCALATION_RATIO = 1.15      # Energy must grow by 15% to count as "escalating"
FADING_RATIO = 0.85          # Energy must drop by 15% to count as "fading"


# ──────────────────────────────────────────────────────────────────
#  CORE ANALYSIS
# ──────────────────────────────────────────────────────────────────

def analyze_chunk(audio_chunk, sample_rate=SAMPLE_RATE):
    """
    Analyze a single audio chunk for siren-band energy.

    Parameters
    ----------
    audio_chunk : np.ndarray  shape (N,) — mono audio samples
    sample_rate : int

    Returns
    -------
    dict with "siren_energy", "total_energy", "confidence",
         "peak_frequency_hz"
    """
    # FFT
    fft_vals = np.fft.rfft(audio_chunk)
    fft_mag = np.abs(fft_vals)
    freqs = np.fft.rfftfreq(len(audio_chunk), d=1.0 / sample_rate)

    # Total energy (for normalization)
    total_energy = np.sum(fft_mag ** 2)
    if total_energy == 0:
        return {"siren_energy": 0, "total_energy": 0, "confidence": 0, "peak_frequency_hz": 0}

    # Siren band energy
    siren_mask = (freqs >= SIREN_LOW) & (freqs <= SIREN_HIGH)
    siren_energy = np.sum(fft_mag[siren_mask] ** 2)

    # Normalized ratio
    ratio = siren_energy / total_energy
    confidence = min(ratio * 3.0, 1.0)  # Scale up; pure siren ≈ 0.33 ratio

    # Peak frequency in siren band
    peak_idx = np.argmax(fft_mag[siren_mask]) if np.any(siren_mask) else 0
    siren_freqs = freqs[siren_mask]
    peak_freq = float(siren_freqs[peak_idx]) if len(siren_freqs) > 0 else 0

    return {
        "siren_energy": float(siren_energy),
        "total_energy": float(total_energy),
        "confidence": float(confidence),
        "peak_frequency_hz": peak_freq,
    }


def determine_volume_trend(energy_history):
    """
    Analyze recent energy readings to determine if the siren is
    approaching (escalating), stationary (stable), or leaving (fading).

    Parameters
    ----------
    energy_history : list[float]  — recent siren_energy values

    Returns
    -------
    str  "escalating" | "stable" | "fading"
    """
    if len(energy_history) < 3:
        return "stable"

    recent = energy_history[-3:]
    older = energy_history[-6:-3] if len(energy_history) >= 6 else energy_history[:3]

    avg_recent = np.mean(recent) if len(recent) > 0 else 0
    avg_older = np.mean(older) if len(older) > 0 else 0

    if avg_older == 0:
        return "stable"

    ratio = avg_recent / avg_older

    if ratio >= ESCALATION_RATIO:
        return "escalating"
    elif ratio <= FADING_RATIO:
        return "fading"
    else:
        return "stable"


# ──────────────────────────────────────────────────────────────────
#  MQTT PUBLISHER
# ──────────────────────────────────────────────────────────────────

def publish_detection(client, detected, frequency_hz, trend, confidence):
    """Publish siren detection event to MQTT."""
    payload = {
        "detected": detected,
        "frequency_hz": round(frequency_hz, 1),
        "volume_trend": trend,
        "confidence": round(confidence, 3),
        "timestamp": time.time(),
    }
    client.publish(TOPIC, json.dumps(payload))
    if detected:
        log.info("🔊 SIREN DETECTED — freq: %.0f Hz, trend: %s, conf: %.0f%%",
                 frequency_hz, trend, confidence * 100)


# ──────────────────────────────────────────────────────────────────
#  DEMO / SIMULATION MODE
# ──────────────────────────────────────────────────────────────────

def run_demo_simulation(mqtt_client, wav_path=None):
    """
    Run the siren detector on a WAV file or synthetic test signal.
    Useful for hackathon demos without a physical I2S microphone.
    """
    log.info("Starting DEMO siren detection...")

    if wav_path and os.path.exists(wav_path):
        try:
            import wave
            wf = wave.open(wav_path, "rb")
            sr = wf.getframerate()
            chunk_size = int(sr * CHUNK_DURATION)
            energy_history = []

            while True:
                raw = wf.readframes(chunk_size)
                if len(raw) == 0:
                    break
                audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                result = analyze_chunk(audio, sr)
                energy_history.append(result["siren_energy"])
                trend = determine_volume_trend(energy_history)

                if result["confidence"] >= CONFIDENCE_THRESHOLD:
                    publish_detection(mqtt_client, True, result["peak_frequency_hz"], trend, result["confidence"])
                else:
                    publish_detection(mqtt_client, False, 0, "stable", result["confidence"])

                time.sleep(CHUNK_DURATION)

            wf.close()
        except ImportError:
            log.warning("wave module not available for WAV playback.")
    else:
        # Generate a synthetic siren signal (1350 Hz, escalating volume)
        log.info("No WAV file provided — generating synthetic siren signal for demo.")
        energy_history = []
        for i in range(20):
            t = np.arange(CHUNK_SIZE) / SAMPLE_RATE
            amplitude = 0.1 + (i * 0.04)  # Escalating volume
            signal = amplitude * np.sin(2 * np.pi * 1350 * t)
            signal += np.random.normal(0, 0.02, len(signal))  # Background noise

            result = analyze_chunk(signal, SAMPLE_RATE)
            energy_history.append(result["siren_energy"])
            trend = determine_volume_trend(energy_history)

            detected = result["confidence"] >= CONFIDENCE_THRESHOLD
            publish_detection(mqtt_client, detected, result["peak_frequency_hz"], trend, result["confidence"])
            time.sleep(CHUNK_DURATION)


# ──────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import paho.mqtt.client as mqtt_lib

    client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        log.info("Connected to MQTT broker at %s:%d", BROKER, PORT)
    except Exception as e:
        log.error("Cannot connect to MQTT broker: %s", e)
        exit(1)

    # Run demo (pass a WAV file path as argument for real audio)
    import sys
    wav = sys.argv[1] if len(sys.argv) > 1 else None
    run_demo_simulation(client, wav)

    client.loop_stop()
    client.disconnect()
