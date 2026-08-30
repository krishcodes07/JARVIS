/**
 * Audio Service — browser microphone capture, live speech-to-text, real-time FFT
 * levels for the orb, and 16 kHz PCM WAV encoding for the /voice/transcribe API.
 */

function encodeWAV(samples: Float32Array, sampleRate: number = 16000): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  // RIFF identifier
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');

  // fmt subchunk
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // 16-bit

  // data subchunk
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);

  // Write PCM samples
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}

function downsampleBuffer(
  buffer: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number = 16000
): Float32Array {
  if (outputSampleRate === inputSampleRate) {
    return buffer;
  }
  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

/**
 * AudioWorklet processor source, loaded from a blob URL so no extra static asset
 * has to be published. Forwards mono frames to the main thread and stays silent
 * on its own output.
 */
const CAPTURE_WORKLET_SRC = `
class JarvisCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel && channel.length) {
      this.port.postMessage(new Float32Array(channel));
    }
    return true;
  }
}
registerProcessor('jarvis-capture', JarvisCaptureProcessor);
`;

let workletUrl: string | null = null;
function getWorkletUrl(): string {
  if (!workletUrl) {
    workletUrl = URL.createObjectURL(
      new Blob([CAPTURE_WORKLET_SRC], { type: 'application/javascript' })
    );
  }
  return workletUrl;
}

/**
 * Voice-activity detection, used by the hands-free voice session to decide when
 * an utterance has finished so it can be sent without the user pressing
 * anything. Levels come from the analyser that already drives the orb, so this
 * costs nothing extra per frame.
 */
export interface VoiceActivityOptions {
  /** Fires once per utterance, after {@link silenceMs} of quiet following speech. */
  onSpeechEnd?: () => void;
  /** Fires once, the first time real speech is confirmed. */
  onSpeechStart?: () => void;
  /** Mean spectrum energy (0–255) that counts as speech. */
  threshold?: number;
  /** Quiet time after speech before the utterance is considered over. */
  silenceMs?: number;
  /** Speech must last this long before silence can end it — rejects clicks and pops. */
  minSpeechMs?: number;
  /** Hard stop for one utterance, so a noisy room can't record forever. */
  maxUtteranceMs?: number;
}

const VAD_DEFAULTS = {
  threshold: 16,
  silenceMs: 850,
  minSpeechMs: 250,
  maxUtteranceMs: 25_000,
} as const;

/**
 * Dedicated Real-Time Streaming Browser STT.
 *
 * How it works:
 *   1. Uses the browser's built-in Web Speech API (SpeechRecognition).
 *   2. `continuous = true` + `interimResults = true` → words stream in real-time.
 *   3. A silence timer (default 1.2s) auto-fires `onSpeechEnd` when the user
 *      stops speaking, which triggers sending the message.
 *   4. If the browser kills the session (timeout / error), it auto-restarts.
 */
export class RealtimeSTT {
  private recognition: any = null;
  private isActive = false;
  private silenceTimer: ReturnType<typeof setTimeout> | null = null;
  private silenceDelayMs: number;
  private onTranscript: (text: string) => void;
  private onDone: () => void;
  public transcript = '';
  private hasReceivedSpeech = false;

  constructor(opts: {
    onTranscript: (text: string) => void;
    onDone: () => void;
    silenceMs?: number;
  }) {
    this.onTranscript = opts.onTranscript;
    this.onDone = opts.onDone;
    this.silenceDelayMs = opts.silenceMs ?? 1200;
  }

  start(): boolean {
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) {
      console.warn('[RealtimeSTT] Web Speech API not available in this browser');
      return false;
    }

    this.stop(); // clean up any previous session
    this.isActive = true;
    this.transcript = '';
    this.hasReceivedSpeech = false;

    const rec = new SR();
    this.recognition = rec;
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.lang = 'en-US';

    console.log('[RealtimeSTT] Starting speech recognition...');

    rec.onstart = () => {
      console.log('[RealtimeSTT] ✅ recognition.onstart fired — mic is live');
    };

    rec.onaudiostart = () => {
      console.log('[RealtimeSTT] 🎙️ onaudiostart — audio capture started');
    };

    rec.onspeechstart = () => {
      console.log('[RealtimeSTT] 🗣️ onspeechstart — user started speaking');
    };

    rec.onresult = (event: any) => {
      let finalText = '';
      let interimText = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalText += result[0].transcript;
        } else {
          interimText += result[0].transcript;
        }
      }

      const combined = (finalText + interimText).trim();
      if (combined) {
        this.hasReceivedSpeech = true;
        this.transcript = combined;
        console.log('[RealtimeSTT] 📝 transcript:', combined);
        this.onTranscript(combined);

        // Reset silence timer on every new word
        this.clearSilenceTimer();
        this.silenceTimer = setTimeout(() => {
          if (this.isActive && this.transcript.trim()) {
            console.log(`[RealtimeSTT] ⏱️ ${this.silenceDelayMs}ms silence → auto-stopping`);
            const finalTranscript = this.transcript;
            this.stop();
            this.onDone();
          }
        }, this.silenceDelayMs);
      }
    };

    rec.onspeechend = () => {
      console.log('[RealtimeSTT] 🔇 onspeechend — browser detected speech ended');
    };

    rec.onerror = (e: any) => {
      if (e.error === 'no-speech') {
        console.log('[RealtimeSTT] ⏳ no-speech timeout (normal, will restart)');
        return;
      }
      if (e.error === 'aborted') {
        console.log('[RealtimeSTT] aborted');
        return;
      }
      if (e.error === 'network') {
        console.log('[RealtimeSTT] ⚠️ network error (Google cloud STT) — will retry once');
        // Mark so onend knows to retry just once, not loop forever
        (rec as any)._networkRetry = ((rec as any)._networkRetry || 0) + 1;
        return;
      }
      console.warn('[RealtimeSTT] ❌ error:', e.error);
    };

    rec.onend = () => {
      console.log('[RealtimeSTT] onend fired. isActive:', this.isActive, 'hasReceivedSpeech:', this.hasReceivedSpeech);
      if (!this.isActive) return;

      const networkRetries = (rec as any)._networkRetry || 0;

      if (this.hasReceivedSpeech) {
        // Speech was detected; silence timer handles the rest
        return;
      }

      // Restart if: no-speech timeout OR first 2 network retries
      if (networkRetries <= 2) {
        console.log('[RealtimeSTT] 🔄 Restarting...');
        setTimeout(() => {
          if (this.isActive) {
            try { rec.start(); } catch { /* already running */ }
          }
        }, networkRetries > 0 ? 1000 : 200);
      } else {
        console.warn('[RealtimeSTT] Too many network errors, stopping retries');
      }
    };

    try {
      rec.start();
      console.log('[RealtimeSTT] rec.start() called successfully');
      return true;
    } catch (err) {
      console.error('[RealtimeSTT] Failed to start:', err);
      return false;
    }
  }

  stop(): string {
    this.isActive = false;
    this.clearSilenceTimer();
    if (this.recognition) {
      try { this.recognition.abort(); } catch { /* ok */ }
      this.recognition = null;
    }
    console.log('[RealtimeSTT] Stopped. Final transcript:', this.transcript);
    return this.transcript;
  }

  private clearSilenceTimer() {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
  }
}

export class AudioService {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private silentSink: GainNode | null = null;
  private microphoneStream: MediaStream | null = null;
  private currentAudio: HTMLAudioElement | null = null;
  private recordedSamples: Float32Array[] = [];
  private totalSampleCount = 0;
  private realtimeSTT: RealtimeSTT | null = null;
  private frameHandle: number | null = null;
  private speechEndCallback: (() => void) | null = null;

  public get isRecording(): boolean {
    return this.microphoneStream !== null;
  }

  public getLatestTranscript(): string {
    return this.realtimeSTT?.transcript || '';
  }

  public async startRecording(
    onFrequencyData?: (data: Uint8Array) => void,
    onLiveTranscript?: (text: string) => void,
    vad?: VoiceActivityOptions
  ): Promise<void> {
    this.recordedSamples = [];
    this.totalSampleCount = 0;
    this.speechEndCallback = null;

    // ── Step 1: Get microphone access FIRST ──
    // This ensures the browser grants mic permission before SpeechRecognition starts.
    try {
      this.microphoneStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
          channelCount: 1,
        },
      });
      console.log('[AudioService] ✅ Microphone access granted');

      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.audioContext = ctx;
      if (ctx.state === 'suspended') {
        await ctx.resume().catch(() => {});
      }

      this.source = ctx.createMediaStreamSource(this.microphoneStream);

      this.analyser = ctx.createAnalyser();
      this.analyser.fftSize = 64;
      this.analyser.smoothingTimeConstant = 0.75;
      this.source.connect(this.analyser);

      this.silentSink = ctx.createGain();
      this.silentSink.gain.value = 0;
      this.silentSink.connect(ctx.destination);

      await this.attachCaptureNode(ctx);

      if (onFrequencyData || vad?.onSpeechEnd || vad?.onSpeechStart) {
        this.startLevelLoop(onFrequencyData, vad);
      }

      // ── Step 2: Start real-time streaming browser STT AFTER mic is granted ──
      // SpeechRecognition must start AFTER getUserMedia so browser mic is already active.
      this.realtimeSTT = new RealtimeSTT({
        onTranscript: (text) => {
          console.log('[AudioService] Live transcript:', text);
          onLiveTranscript?.(text);
        },
        onDone: () => {
          console.log('[AudioService] RealtimeSTT auto-stop triggered → finalising utterance');
          vad?.onSpeechEnd?.();
        },
        silenceMs: 1200,
      });
      this.realtimeSTT.start();

    } catch (e) {
      console.error('Microphone error:', e);
      this.cleanupStream();
      throw e;
    }
  }

  /** Prefer AudioWorklet; fall back to the deprecated ScriptProcessor. */
  private async attachCaptureNode(ctx: AudioContext): Promise<void> {
    const collect = (frame: Float32Array) => {
      this.recordedSamples.push(frame);
      this.totalSampleCount += frame.length;
    };

    if (ctx.audioWorklet) {
      try {
        await ctx.audioWorklet.addModule(getWorkletUrl());
        const node = new AudioWorkletNode(ctx, 'jarvis-capture', {
          numberOfInputs: 1,
          numberOfOutputs: 1,
          channelCount: 1,
        });
        node.port.onmessage = (event) => {
          const data = event.data;
          if (data instanceof Float32Array && data.length) collect(data);
        };
        this.source?.connect(node);
        if (this.silentSink) node.connect(this.silentSink);
        this.workletNode = node;
        return;
      } catch (err) {
        console.warn('AudioWorklet unavailable, falling back to ScriptProcessor:', err);
      }
    }

    const processor = ctx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      const copy = new Float32Array(inputData.length);
      copy.set(inputData);
      collect(copy);
    };
    this.source?.connect(processor);
    if (this.silentSink) processor.connect(this.silentSink);
    this.processor = processor;
  }

  private startLevelLoop(
    onFrequencyData?: (data: Uint8Array) => void,
    vad?: VoiceActivityOptions
  ): void {
    this.stopLevelLoop();
    const bufferLength = this.analyser?.frequencyBinCount ?? 32;
    // One reused buffer — the consumer copies if it needs to retain the values.
    const dataArray = new Uint8Array(bufferLength);

    const silenceMs = vad?.silenceMs ?? VAD_DEFAULTS.silenceMs;
    const minSpeechMs = vad?.minSpeechMs ?? VAD_DEFAULTS.minSpeechMs;
    const maxUtteranceMs = vad?.maxUtteranceMs ?? VAD_DEFAULTS.maxUtteranceMs;
    const watchActivity = !!(vad?.onSpeechEnd || vad?.onSpeechStart);

    const openedAt = performance.now();
    let lastTick = openedAt;
    let speechMs = 0;
    let quietSince: number | null = null;
    let speechAnnounced = false;
    let ended = false;

    // Adaptive noise floor tracking (calibrates to ambient mic/room noise)
    let noiseFloor = 15;
    let calibrationFrames = 0;

    const triggerSpeechEnd = () => {
      if (!ended) {
        ended = true;
        this.speechEndCallback = null;
        this.stopLevelLoop();
        vad?.onSpeechEnd?.();
      }
    };
    this.speechEndCallback = triggerSpeechEnd;

    const tick = () => {
      if (!this.analyser || !this.microphoneStream?.active) {
        this.frameHandle = null;
        return;
      }
      this.analyser.getByteFrequencyData(dataArray);
      onFrequencyData?.(dataArray);

      if (watchActivity && !ended) {
        const now = performance.now();
        // Clamp the delta: a backgrounded tab throttles rAF, and un-clamped
        // gaps would bank enough "silence" to end the turn on the first frame back.
        const delta = Math.min(now - lastTick, 250);
        lastTick = now;

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        const level = sum / dataArray.length;

        // Dynamic noise floor calibration
        if (now - openedAt < 350) {
          noiseFloor = (noiseFloor * calibrationFrames + level) / (calibrationFrames + 1);
          calibrationFrames++;
        } else if (level < noiseFloor) {
          noiseFloor = noiseFloor * 0.90 + level * 0.10;
        } else if (quietSince !== null) {
          noiseFloor = noiseFloor * 0.98 + level * 0.02;
        }

        // Fallback Audio Energy VAD (if RealtimeSTT is unavailable)
        const speechThreshold = Math.max(vad?.threshold ?? VAD_DEFAULTS.threshold, noiseFloor + 8);

        if (level > speechThreshold) {
          speechMs += delta;
          quietSince = null;
          if (!speechAnnounced && speechMs >= minSpeechMs) {
            speechAnnounced = true;
            vad?.onSpeechStart?.();
          }
        } else if (speechAnnounced) {
          // In silence (below speech threshold):
          if (quietSince === null) {
            quietSince = now;
          } else if (now - quietSince >= silenceMs) {
            triggerSpeechEnd();
            return;
          }
        }

        if (!ended && speechAnnounced && now - openedAt >= maxUtteranceMs) {
          triggerSpeechEnd();
          return;
        }
      }

      this.frameHandle = requestAnimationFrame(tick);
    };
    this.frameHandle = requestAnimationFrame(tick);
  }

  private stopLevelLoop(): void {
    if (this.frameHandle !== null) {
      cancelAnimationFrame(this.frameHandle);
      this.frameHandle = null;
    }
  }

  public async stopRecording(): Promise<Blob> {
    if (this.realtimeSTT) {
      this.realtimeSTT.stop();
      this.realtimeSTT = null;
    }

    const inputRate = this.audioContext?.sampleRate || 44100;

    // Merge recorded Float32 samples
    const merged = new Float32Array(this.totalSampleCount);
    let offset = 0;
    for (const chunk of this.recordedSamples) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    this.cleanupStream();

    // Downsample to 16kHz and convert to valid PCM WAV Blob
    const downsampled = downsampleBuffer(merged, inputRate, 16000);
    return encodeWAV(downsampled, 16000);
  }

  /** Abandon the current capture without producing a blob. */
  public cancelRecording(): void {
    if (this.realtimeSTT) {
      this.realtimeSTT.stop();
      this.realtimeSTT = null;
    }
    this.recordedSamples = [];
    this.totalSampleCount = 0;
    this.cleanupStream();
  }

  public playAudio(blob: Blob): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.currentAudio) {
        this.currentAudio.pause();
        this.currentAudio = null;
      }

      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      this.currentAudio = audio;

      audio.onended = () => {
        URL.revokeObjectURL(url);
        this.currentAudio = null;
        resolve();
      };

      audio.onerror = (e) => {
        URL.revokeObjectURL(url);
        this.currentAudio = null;
        reject(e);
      };

      audio.play().catch(reject);
    });
  }

  public stopAudio(): void {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
  }

  private cleanupStream(): void {
    this.stopLevelLoop();

    if (this.workletNode) {
      this.workletNode.port.onmessage = null;
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.processor) {
      this.processor.onaudioprocess = null;
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    if (this.silentSink) {
      this.silentSink.disconnect();
      this.silentSink = null;
    }
    if (this.microphoneStream) {
      this.microphoneStream.getTracks().forEach((track) => track.stop());
      this.microphoneStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
  }
}

export const audioService = new AudioService();
