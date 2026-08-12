"use client";

// Captures raw PCM via the Web Audio API and encodes real 16-bit WAV files in-browser,
// rather than using MediaRecorder's compressed webm/opus output. Stage 3's DSP work
// (librosa/Parselmouth) needs precise, uncompressed samples, so it's better to produce WAV
// from day one than re-encode later.
//
// Uses ScriptProcessorNode rather than the more modern AudioWorkletNode — it's deprecated
// but still fully functional in every current browser, and avoids the extra complexity of
// loading a separate worklet module file for this stage. Worth revisiting later.

export class MicrophonePermissionDeniedError extends Error {}
export class MicrophoneUnavailableError extends Error {}

export interface QuickQualityCheck {
  clipping: boolean;
  tooQuiet: boolean;
  tooShort: boolean;
  peakAmplitude: number;
  rms: number;
  durationSeconds: number;
}

export interface RecordingResult {
  wavBytes: ArrayBuffer;
  sampleRate: number;
  channels: number;
  quality: QuickQualityCheck;
}

const CLIPPING_SAMPLE_THRESHOLD = 0.99;
const CLIPPING_FRACTION_THRESHOLD = 0.001;
const TOO_QUIET_RMS_THRESHOLD = 0.01;
const MIN_DURATION_SECONDS = 0.4;
const PROCESSOR_BUFFER_SIZE = 4096;

export class AudioRecorder {
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private silentGain: GainNode | null = null;
  private chunks: Float32Array[] = [];

  /** Called on the audio thread's cadence (~every 90ms at 44.1kHz) with the latest chunk,
   * for live waveform rendering. Do cheap work here — no React state updates. */
  onChunk: ((chunk: Float32Array) => void) | null = null;

  async requestPermissionAndPrepare(): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      if (err instanceof DOMException) {
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          throw new MicrophonePermissionDeniedError("Microphone permission was denied.");
        }
        if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
          throw new MicrophoneUnavailableError("No microphone was found.");
        }
      }
      throw err;
    }
  }

  getMicrophoneLabel(): string | null {
    return this.stream?.getAudioTracks()[0]?.label || null;
  }

  /** Only meaningful while recording (between start() and stop()) — null otherwise. */
  getSampleRate(): number | null {
    return this.audioContext?.sampleRate ?? null;
  }

  start(): void {
    if (!this.stream) {
      throw new Error("Call requestPermissionAndPrepare() before start().");
    }
    const AudioContextCtor =
      window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.audioContext = new AudioContextCtor();
    this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);
    this.processorNode = this.audioContext.createScriptProcessor(PROCESSOR_BUFFER_SIZE, 1, 1);
    this.chunks = [];

    this.processorNode.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      this.chunks.push(new Float32Array(input)); // copy — the buffer is reused by the browser
      this.onChunk?.(input);
    };

    // ScriptProcessorNode only fires onaudioprocess while connected to a destination in
    // some browsers. Route through a silent gain node so the mic doesn't feed back into
    // the speakers.
    this.silentGain = this.audioContext.createGain();
    this.silentGain.gain.value = 0;
    this.sourceNode.connect(this.processorNode);
    this.processorNode.connect(this.silentGain);
    this.silentGain.connect(this.audioContext.destination);
  }

  stop(): RecordingResult {
    if (!this.audioContext || !this.processorNode || !this.sourceNode) {
      throw new Error("start() was never called.");
    }
    this.processorNode.disconnect();
    this.sourceNode.disconnect();
    this.silentGain?.disconnect();

    const sampleRate = this.audioContext.sampleRate;
    const samples = concatenate(this.chunks);
    const quality = quickQualityCheck(samples, sampleRate);
    const wavBytes = encodeWav(samples, sampleRate, 1);

    this.audioContext.close();
    this.audioContext = null;
    this.processorNode = null;
    this.sourceNode = null;

    return { wavBytes, sampleRate, channels: 1, quality };
  }

  /** Releases the microphone. Call when leaving the recording flow entirely. */
  release(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
  }
}

function concatenate(chunks: Float32Array[]): Float32Array {
  const total = chunks.reduce((sum, c) => sum + c.length, 0);
  const result = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return result;
}

export function quickQualityCheck(samples: Float32Array, sampleRate: number): QuickQualityCheck {
  if (samples.length === 0) {
    return { clipping: false, tooQuiet: true, tooShort: true, peakAmplitude: 0, rms: 0, durationSeconds: 0 };
  }

  let peak = 0;
  let sumSquares = 0;
  let clippedCount = 0;
  for (let i = 0; i < samples.length; i++) {
    const abs = Math.abs(samples[i]);
    if (abs > peak) peak = abs;
    sumSquares += samples[i] * samples[i];
    if (abs >= CLIPPING_SAMPLE_THRESHOLD) clippedCount++;
  }
  const rms = Math.sqrt(sumSquares / samples.length);
  const durationSeconds = samples.length / sampleRate;

  return {
    clipping: clippedCount / samples.length > CLIPPING_FRACTION_THRESHOLD,
    tooQuiet: rms < TOO_QUIET_RMS_THRESHOLD,
    tooShort: durationSeconds < MIN_DURATION_SECONDS,
    peakAmplitude: peak,
    rms,
    durationSeconds,
  };
}

export function encodeWav(samples: Float32Array, sampleRate: number, channels: number): ArrayBuffer {
  const bytesPerSample = 2;
  const blockAlign = channels * bytesPerSample;
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true); // byte rate
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bytesPerSample * 8, true); // bits per sample
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, clamped * 32767, true);
    offset += 2;
  }

  return buffer;
}

function writeString(view: DataView, offset: number, text: string): void {
  for (let i = 0; i < text.length; i++) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
}
