import React, { useState } from 'react';
import {
  Check,
  CheckCircle2,
  ChevronRight,
  Edit3,
  HelpCircle,
  MessageSquare,
  Sparkles,
} from 'lucide-react';
import { useJarvis } from '../../context/JarvisContext';
import { QuestionItem, ToolCall } from '../../types';
import { cn } from '../../utils/cn';
import { Button } from '../ui/Button';

export interface AskUserCardProps {
  toolCall: ToolCall;
}

export const AskUserCard: React.FC<AskUserCardProps> = ({ toolCall }) => {
  const { respondToAskUser } = useJarvis();

  // Extract questions from toolCall.questions or toolCall.args
  const rawQuestions: QuestionItem[] =
    toolCall.questions ||
    toolCall.args?.questions ||
    (toolCall.args?.question
      ? [
          {
            id: 'q_0',
            question: toolCall.args.question,
            options: toolCall.args.options || [],
            is_multi_select: toolCall.args.is_multi_select || false,
            header: toolCall.args.title || 'Question',
          },
        ]
      : []);

  const [currentStep, setCurrentStep] = useState<number>(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [isCustomMode, setIsCustomMode] = useState<boolean>(false);
  const [customText, setCustomText] = useState<string>('');
  const [submitted, setSubmitted] = useState<boolean>(toolCall.status === 'completed');

  const totalSteps = rawQuestions.length;
  const currentQ: QuestionItem | undefined = rawQuestions[currentStep];

  // If completed, format existing answers or result
  const isFinished = submitted || toolCall.status === 'completed';

  const handleSelectOption = (opt: string) => {
    if (isFinished) return;
    setIsCustomMode(false);
    setSelectedOption(opt);
  };

  const handleSelectCustom = () => {
    if (isFinished) return;
    setIsCustomMode(true);
    setSelectedOption('__custom__');
  };

  const handleNextOrSubmit = () => {
    if (!currentQ || isFinished) return;

    const answerVal = isCustomMode ? customText.trim() || '(Custom response: blank)' : selectedOption;
    if (!answerVal) return;

    const qKey = currentQ.question;
    const newAnswers = { ...answers, [qKey]: answerVal };
    setAnswers(newAnswers);

    if (currentStep + 1 < totalSteps) {
      setCurrentStep((prev) => prev + 1);
      setSelectedOption('');
      setIsCustomMode(false);
      setCustomText('');
    } else {
      // Final submission
      setSubmitted(true);
      if (toolCall.prompt_id) {
        respondToAskUser(toolCall.prompt_id, newAnswers);
      }
    }
  };

  if (!rawQuestions || rawQuestions.length === 0) {
    return null;
  }

  // Completed State View
  if (isFinished) {
    return (
      <div className="my-2.5 overflow-hidden rounded-2xl border border-success/30 bg-surface-2/60 p-4 shadow-lg backdrop-blur-md transition-all">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-success/15 text-success">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-success">
                JARVIS Decision Recorded
              </span>
              <span className="rounded-full bg-surface-3/80 px-2 py-0.5 text-[10px] font-mono text-content-muted">
                Completed
              </span>
            </div>
            <div className="mt-1 text-xs text-content-secondary">
              {Object.keys(answers).length > 0 ? (
                <div className="mt-1 space-y-1">
                  {Object.entries(answers).map(([q, ans], idx) => (
                    <div key={idx} className="flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="text-content-muted">{q}:</span>
                      <span className="rounded-md bg-accent/15 px-2 py-0.5 font-medium text-accent">
                        {ans}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="font-mono text-content-secondary">{toolCall.result || 'Response provided.'}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const currentChoice = isCustomMode ? customText.trim() : selectedOption;
  const canProceed = Boolean(currentChoice);

  return (
    <div className="my-3 overflow-hidden rounded-2xl border border-accent/40 bg-surface-2/80 p-4 shadow-[0_0_30px_rgba(6,182,212,0.12)] backdrop-blur-xl transition-all">
      {/* Header Badge & Steps */}
      <div className="flex items-center justify-between border-b border-subtle/10 pb-3">
        <div className="flex items-center gap-2">
          <div className="relative flex h-7 w-7 items-center justify-center rounded-lg bg-accent/20 text-accent">
            <Sparkles className="h-4 w-4 animate-pulse" />
            <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-accent">
                JARVIS Direct Inquiry
              </span>
            </div>
            <p className="text-[11px] text-content-muted">Your input is required to continue</p>
          </div>
        </div>

        {totalSteps > 1 && (
          <div className="flex items-center gap-1.5 rounded-full bg-surface-3/80 px-2.5 py-1 text-[10px] font-medium text-content-secondary">
            <span>Step {currentStep + 1} of {totalSteps}</span>
            <div className="flex items-center gap-1 ml-1">
              {rawQuestions.map((_, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'h-1.5 w-1.5 rounded-full transition-all',
                    idx === currentStep
                      ? 'w-3 bg-accent'
                      : idx < currentStep
                      ? 'bg-success'
                      : 'bg-content-muted/30'
                  )}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Question Prompt */}
      {currentQ && (
        <div className="py-3">
          {currentQ.header && (
            <span className="inline-block text-[11px] font-semibold uppercase tracking-wider text-accent-soft mb-1">
              {currentQ.header}
            </span>
          )}
          <h4 className="text-sm font-semibold text-content leading-snug">
            {currentQ.question}
          </h4>

          {/* Options Grid */}
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {(currentQ.options || []).map((opt, idx) => {
              const isSelected = !isCustomMode && selectedOption === opt;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectOption(opt)}
                  className={cn(
                    'group relative flex items-center justify-between rounded-xl border px-3 py-2.5 text-left text-xs transition-all duration-200',
                    isSelected
                      ? 'border-accent bg-accent/15 text-content shadow-[0_0_15px_rgba(6,182,212,0.25)] ring-1 ring-accent'
                      : 'border-subtle/15 bg-surface-3/50 text-content-secondary hover:border-accent/40 hover:bg-surface-3/80 hover:text-content'
                  )}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span
                      className={cn(
                        'flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-mono font-bold transition-colors',
                        isSelected
                          ? 'bg-accent text-void'
                          : 'bg-surface-2 text-content-muted group-hover:bg-accent/20 group-hover:text-accent'
                      )}
                    >
                      {idx + 1}
                    </span>
                    <span className="truncate font-medium">{opt}</span>
                  </div>
                  {isSelected && <Check className="h-4 w-4 shrink-0 text-accent" />}
                </button>
              );
            })}

            {/* Fixed Custom Option */}
            <button
              type="button"
              onClick={handleSelectCustom}
              className={cn(
                'group relative flex items-center justify-between rounded-xl border px-3 py-2.5 text-left text-xs transition-all duration-200',
                isCustomMode
                  ? 'border-warning/60 bg-warning/15 text-content shadow-[0_0_15px_rgba(245,158,11,0.25)] ring-1 ring-warning/60'
                  : 'border-dashed border-warning/30 bg-warning/[0.04] text-warning hover:border-warning/60 hover:bg-warning/[0.08]'
              )}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span
                  className={cn(
                    'flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-mono font-bold transition-colors',
                    isCustomMode ? 'bg-warning text-void' : 'bg-warning/20 text-warning'
                  )}
                >
                  C
                </span>
                <span className="truncate font-medium">Custom (Type your own)</span>
              </div>
              <Edit3 className="h-3.5 w-3.5 shrink-0 text-warning" />
            </button>
          </div>

          {/* Custom Input Field */}
          {isCustomMode && (
            <div className="mt-3 animate-in fade-in slide-in-from-top-2 duration-200">
              <div className="relative rounded-xl border border-warning/50 bg-surface-3/90 p-2 focus-within:ring-2 focus-within:ring-warning/40">
                <input
                  type="text"
                  autoFocus
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && customText.trim()) {
                      e.preventDefault();
                      handleNextOrSubmit();
                    }
                  }}
                  placeholder="Type your custom response and press Enter..."
                  className="w-full bg-transparent px-2 py-1 text-xs text-content placeholder:text-content-muted outline-none"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer Navigation */}
      <div className="mt-2 flex items-center justify-between border-t border-subtle/10 pt-3">
        <div className="flex items-center gap-1.5 text-[11px] text-content-muted">
          <HelpCircle className="h-3.5 w-3.5" />
          <span>Select an option or type custom</span>
        </div>

        <div className="flex items-center gap-2">
          {currentStep > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setCurrentStep((prev) => prev - 1);
                setSelectedOption('');
                setIsCustomMode(false);
                setCustomText('');
              }}
            >
              Back
            </Button>
          )}

          <Button
            size="sm"
            variant="primary"
            disabled={!canProceed}
            icon={currentStep + 1 < totalSteps ? <ChevronRight /> : <Check />}
            onClick={handleNextOrSubmit}
            className="shadow-accent-sm"
          >
            {currentStep + 1 < totalSteps ? 'Next Question' : 'Confirm Choice'}
          </Button>
        </div>
      </div>
    </div>
  );
};
