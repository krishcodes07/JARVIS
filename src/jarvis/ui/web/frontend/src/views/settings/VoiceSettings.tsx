import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Ear, Loader2, Mic, Play, Speaker, Volume2 } from 'lucide-react';
import { ConfigApi, VoiceApi } from '../../services/api';
import { VoiceOption } from '../../types';
import { cn } from '../../utils/cn';
import { Badge, Button, Row, Section, Select, SkeletonRows, TextField, Toggle } from '../../components/ui';

/**
 * Local mirror of the `voice` section of jarvis.yaml.
 *
 * Only the fields this panel edits are represented — everything else in
 * `VoiceConfig` is left untouched by the deep-merge PATCH.
 */
interface VoiceDraft {
  enabled: boolean;
  auto_send_msg: boolean;
  max_speak_characters: number;
  tts: { provider: string; voice: string; rate: string; stream: boolean };
  stt: { provider: string; engine: string; model: string; language: string };
}

const DEFAULT_DRAFT: VoiceDraft = {
  enabled: false,
  auto_send_msg: true,
  max_speak_characters: 10000,
  tts: { provider: 'edge_tts', voice: 'en-US-JennyNeural', rate: '+0%', stream: true },
  stt: { provider: 'sr', engine: 'google', model: 'base', language: 'en-US' },
};

const TTS_PROVIDERS = [
  { value: 'edge_tts', label: 'Microsoft Edge TTS — free neural voices' },
  { value: 'elevenlabs', label: 'ElevenLabs — high fidelity (API key)' },
];

// Values must match STTConfig.provider in core/config.py: "sr" | "whisper".
const STT_PROVIDERS = [
  { value: 'sr', label: 'SpeechRecognition — cloud or local engines' },
  { value: 'whisper', label: 'Faster-Whisper — fully local' },
];

const SR_ENGINES = [
  { value: 'google', label: 'Google Web Speech (online, no key)' },
  { value: 'whisper', label: 'Whisper via SpeechRecognition' },
  { value: 'sphinx', label: 'CMU Sphinx (offline)' },
  { value: 'vosk', label: 'Vosk (offline)' },
];

const WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large-v3'].map((m) => ({
  value: m,
  label: m,
}));

const RATES = ['-25%', '-10%', '+0%', '+10%', '+25%', '+50%'].map((r) => ({
  value: r,
  label: r === '+0%' ? 'Normal' : r,
}));

const SAMPLE_TEXT = 'All systems are online. How can I help you today?';

export const VoiceSettings: React.FC = () => {
  const [draft, setDraft] = useState<VoiceDraft>(DEFAULT_DRAFT);
  const [baseline, setBaseline] = useState<VoiceDraft>(DEFAULT_DRAFT);
  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(true);
  const [voicesError, setVoicesError] = useState('');
  const [locale, setLocale] = useState('all');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);

  // One reusable element so a second preview interrupts the first.
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  // Read inside the voice-loading effect without making it re-run on every keystroke.
  const voiceIdRef = useRef('');
  useEffect(() => {
    voiceIdRef.current = draft.tts.voice;
  }, [draft.tts.voice]);

  // Provider whose catalogue we have already reconciled against the draft. Null
  // until the first load, which is how we avoid clearing the *saved* voice id.
  const reconciledRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const cfg = await ConfigApi.get().catch(() => null);
      if (cancelled) return;

      if (cfg?.voice) {
        const v = cfg.voice;
        const next: VoiceDraft = {
          enabled: !!v.enabled,
          auto_send_msg: v.auto_send_msg ?? true,
          max_speak_characters: v.max_speak_characters ?? 10000,
          tts: {
            provider: v.tts?.provider || DEFAULT_DRAFT.tts.provider,
            voice: v.tts?.voice || '',
            rate: v.tts?.rate || '+0%',
            stream: v.tts?.stream ?? true,
          },
          stt: {
            provider: v.stt?.provider || DEFAULT_DRAFT.stt.provider,
            engine: v.stt?.engine || DEFAULT_DRAFT.stt.engine,
            model: v.stt?.model || DEFAULT_DRAFT.stt.model,
            language: v.stt?.language || DEFAULT_DRAFT.stt.language,
          },
        };
        setDraft(next);
        setBaseline(next);
        voiceIdRef.current = next.tts.voice;
      }

      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const provider = draft.tts.provider;

  /**
   * Reload the catalogue whenever the TTS provider changes.
   *
   * This is the whole point of the provider-scoped `/api/voice/voices?provider=`
   * endpoint: picking ElevenLabs has to show ElevenLabs voices immediately, before
   * anything is saved and even while voice output is disabled.
   */
  useEffect(() => {
    if (loading) return; // wait until the saved provider is known
    let cancelled = false;

    setVoicesLoading(true);
    setVoicesError('');

    void VoiceApi.listVoices(provider)
      .then((list) => {
        if (cancelled) return;
        setVoices(list);

        const current = list.find((v) => v.id === voiceIdRef.current);
        // Open the picker on the locale the selected voice belongs to.
        setLocale(current?.locale || 'all');
        // A voice id from another provider is meaningless here — fall back to the
        // provider default. Skipped on the very first load so a saved-but-unknown
        // id is left alone instead of silently marking the panel dirty.
        if (!current && list.length > 0 && reconciledRef.current !== null) {
          setDraft((prev) =>
            prev.tts.voice ? { ...prev, tts: { ...prev.tts, voice: '' } } : prev
          );
        }
        reconciledRef.current = provider;
      })
      .catch((e: any) => {
        if (cancelled) return;
        setVoices([]);
        setLocale('all');
        // The API returns an actionable detail here (missing ELEVENLABS_API_KEY,
        // provider package not installed, network failure).
        setVoicesError(e?.message || `Could not list ${provider} voices.`);
        reconciledRef.current = provider;
      })
      .finally(() => {
        if (!cancelled) setVoicesLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [provider, loading]);

  // Release the last preview blob when the panel goes away.
  useEffect(
    () => () => {
      audioRef.current?.pause();
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    },
    []
  );

  const patch = useCallback(<K extends keyof VoiceDraft>(key: K, value: VoiceDraft[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setStatus(null);
  }, []);

  const locales = useMemo(() => {
    const set = new Set(voices.map((v) => v.locale).filter(Boolean));
    return ['all', ...Array.from(set).sort()];
  }, [voices]);

  // ElevenLabs voices carry no locale, so the filter would be a dead control.
  const showLocaleFilter = locales.length > 2;

  const visibleVoices = useMemo(
    () => (locale === 'all' ? voices : voices.filter((v) => v.locale === locale)),
    [voices, locale]
  );

  const dirty = JSON.stringify(draft) !== JSON.stringify(baseline);

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const res = await ConfigApi.update({ voice: draft });
      setBaseline(draft);
      if (res.rejected?.length) {
        setStatus({
          ok: false,
          message: `Saved, but these keys were rejected: ${res.rejected.join(', ')}`,
        });
      } else if (draft.enabled && res.voice_reloaded === false) {
        // The engine tried to rebuild the subsystem and could not — usually a
        // missing provider package or API key.
        setStatus({
          ok: false,
          message: 'Saved, but the voice subsystem could not start. Check the provider credentials.',
        });
      } else {
        setStatus({ ok: true, message: 'Voice settings saved and applied.' });
      }
    } catch (e: any) {
      setStatus({ ok: false, message: e.message || 'Could not save voice settings.' });
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    setStatus(null);
    try {
      const blob = await VoiceApi.synthesize(
        SAMPLE_TEXT,
        draft.tts.voice || undefined,
        // Preview the provider that is currently selected, not the saved one.
        draft.tts.provider || undefined
      );
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
      const url = URL.createObjectURL(blob);
      previewUrlRef.current = url;
      if (!audioRef.current) audioRef.current = new Audio();
      audioRef.current.src = url;
      await audioRef.current.play();
    } catch (e: any) {
      setStatus({ ok: false, message: e.message || 'Preview failed — is the TTS provider set up?' });
    } finally {
      setPreviewing(false);
    }
  };

  if (loading) return <SkeletonRows count={6} />;

  return (
    <div className="space-y-7">
      <Section title="Voice mode" icon={<Volume2 />}>
        <Row
          label="Enable voice"
          icon={<Mic />}
          description="Allows JARVIS to listen and speak. The mic button in the composer stays available either way."
          control={<Toggle checked={draft.enabled} onChange={(v) => patch('enabled', v)} />}
        />
        <Row
          label="Send transcript automatically"
          icon={<Ear />}
          description="When off, the transcribed text lands in the composer for you to edit before sending."
          control={
            <Toggle
              checked={draft.auto_send_msg}
              onChange={(v) => patch('auto_send_msg', v)}
            />
          }
        />
        <Row
          label="Spoken response limit"
          icon={<Speaker />}
          description="Characters read aloud per reply. Long answers are truncated for speech only — the text stays complete. 0 removes the cap."
          control={
            <input
              type="number"
              min={0}
              max={100000}
              step={500}
              value={draft.max_speak_characters}
              onChange={(e) => patch('max_speak_characters', Number(e.target.value) || 0)}
              className="h-9 w-24 rounded-lg border border-subtle/15 bg-surface-2 px-2 text-center font-mono text-xs text-content outline-none transition-colors focus:border-accent/50"
            />
          }
        />
      </Section>

      {/* ─── Speech out ─── */}
      <Section
        title="Speech output"
        icon={<Speaker />}
        description="How JARVIS sounds when it reads a reply."
        actions={
          <Button
            size="sm"
            variant="outline"
            icon={previewing ? <Loader2 className="animate-spin" /> : <Play />}
            onClick={() => void handlePreview()}
            disabled={previewing}
          >
            Preview
          </Button>
        }
      >
        <Row
          stacked
          label="Provider"
          description="ElevenLabs needs ELEVENLABS_API_KEY in ~/.jarvis/.env."
          control={
            <Select
              size="sm"
              options={TTS_PROVIDERS}
              value={draft.tts.provider}
              onChange={(e) => patch('tts', { ...draft.tts, provider: e.target.value })}
            />
          }
        />

        <Row
          stacked
          label="Voice"
          description={
            voicesLoading
              ? `Loading ${provider} voices…`
              : voicesError
                ? voicesError
                : voices.length
                  ? showLocaleFilter
                    ? `${visibleVoices.length} of ${voices.length} voices shown.`
                    : `${voices.length} voices available.`
                  : `${provider} reported no voices — enter a voice id by hand.`
          }
          control={
            voicesLoading ? (
              <div className="flex h-9 items-center gap-2 text-xs text-content-muted">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Fetching catalogue…
              </div>
            ) : voices.length ? (
              <div
                className={cn(
                  'grid grid-cols-1 gap-2',
                  showLocaleFilter && 'sm:grid-cols-[9rem_1fr]'
                )}
              >
                {showLocaleFilter && (
                  <Select
                    size="sm"
                    aria-label="Filter voices by locale"
                    options={locales.map((l) => ({
                      value: l,
                      label: l === 'all' ? 'All locales' : l,
                    }))}
                    value={locale}
                    onChange={(e) => setLocale(e.target.value)}
                  />
                )}
                <Select
                  size="sm"
                  aria-label="Voice"
                  options={[
                    { value: '', label: 'Provider default' },
                    ...visibleVoices.map((v) => ({
                      value: v.id,
                      label: `${v.name}${v.gender ? ` · ${v.gender}` : ''}`,
                    })),
                  ]}
                  value={draft.tts.voice}
                  onChange={(e) => patch('tts', { ...draft.tts, voice: e.target.value })}
                />
              </div>
            ) : (
              <TextField
                size="sm"
                value={draft.tts.voice}
                placeholder={provider === 'elevenlabs' ? 'ElevenLabs voice id' : 'en-US-JennyNeural'}
                error={voicesError || undefined}
                onChange={(e) => patch('tts', { ...draft.tts, voice: e.target.value })}
              />
            )
          }
        />

        {draft.tts.provider === 'edge_tts' && (
          <Row
            label="Speaking rate"
            description="Relative to the voice's natural pace."
            control={
              <Select
                size="sm"
                className="w-32"
                options={RATES}
                value={draft.tts.rate}
                onChange={(e) => patch('tts', { ...draft.tts, rate: e.target.value })}
              />
            }
          />
        )}

        <Row
          label="Stream audio"
          description="Start speaking before the whole reply is synthesised. Lower latency, slightly rougher joins."
          control={
            <Toggle
              checked={draft.tts.stream}
              onChange={(v) => patch('tts', { ...draft.tts, stream: v })}
            />
          }
        />
      </Section>

      {/* ─── Speech in ─── */}
      <Section
        title="Speech input"
        icon={<Mic />}
        description="How your microphone audio becomes text."
      >
        <Row
          stacked
          label="Provider"
          control={
            <Select
              size="sm"
              options={STT_PROVIDERS}
              value={draft.stt.provider}
              onChange={(e) => patch('stt', { ...draft.stt, provider: e.target.value })}
            />
          }
        />

        {draft.stt.provider === 'sr' ? (
          <Row
            stacked
            label="Recognition engine"
            description="Google needs a connection; Sphinx and Vosk run offline."
            control={
              <Select
                size="sm"
                options={SR_ENGINES}
                value={draft.stt.engine}
                onChange={(e) => patch('stt', { ...draft.stt, engine: e.target.value })}
              />
            }
          />
        ) : (
          <Row
            label="Model size"
            description="Larger models are more accurate and slower. Downloaded on first use."
            control={
              <Select
                size="sm"
                className="w-32"
                options={WHISPER_MODELS}
                value={draft.stt.model}
                onChange={(e) => patch('stt', { ...draft.stt, model: e.target.value })}
              />
            }
          />
        )}

        <Row
          label="Language"
          description="BCP-47 tag, e.g. en-US, en-IN, hi-IN."
          control={
            <TextField
              size="sm"
              className="w-32 text-center font-mono"
              value={draft.stt.language}
              onChange={(e) => patch('stt', { ...draft.stt, language: e.target.value })}
            />
          }
        />
      </Section>

      {/* ─── Save bar ─── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 text-xs">
          {status ? (
            <span className={cn(status.ok ? 'text-success' : 'text-danger')}>{status.message}</span>
          ) : dirty ? (
            <Badge tone="warning" dot>
              Unsaved changes
            </Badge>
          ) : (
            <span className="text-content-muted">Saved to your JARVIS config.</span>
          )}
        </div>
        <Button
          variant="primary"
          size="sm"
          loading={saving}
          disabled={!dirty}
          onClick={() => void handleSave()}
        >
          Save voice settings
        </Button>
      </div>
    </div>
  );
};
