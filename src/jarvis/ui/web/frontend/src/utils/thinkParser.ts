/**
 * Robust parser for extracting <think> and <thought> tags from LLM reasoning output.
 */

export interface ParsedMessageContent {
  thought?: string;
  content: string;
  isThinking?: boolean;
}

export function parseThinkTags(raw: string, existingThought?: string): ParsedMessageContent {
  if (!raw && !existingThought) {
    return { content: '' };
  }

  let text = raw || '';
  let thought = existingThought || '';

  // 1. Check for complete <think>...</think> or <thought>...</thought> block (including salted variants like <think:abc123>)
  const closedRegex = /<(?:think|thought)(?::[a-zA-Z0-9_-]+)?>([\s\S]*?)<\/(?:think|thought)(?::[a-zA-Z0-9_-]+)?>/i;
  let match = text.match(closedRegex);

  while (match) {
    const extracted = match[1].trim();
    thought = thought ? `${thought}\n\n${extracted}` : extracted;
    text = text.replace(match[0], '').trim();
    match = text.match(closedRegex);
  }

  // 2. Check for open unclosed <think> tag (during streaming, including salted variants)
  const openRegex = /<(?:think|thought)(?::[a-zA-Z0-9_-]+)?>([\s\S]*)$/i;
  const openMatch = text.match(openRegex);
  if (openMatch) {
    const inProgress = openMatch[1].trim();
    thought = thought ? `${thought}\n\n${inProgress}` : inProgress;
    text = text.replace(openRegex, '').trim();
    return {
      thought: thought.trim(),
      content: text,
      isThinking: true,
    };
  }

  return {
    thought: thought ? thought.trim() : undefined,
    content: text.trim(),
    isThinking: false,
  };
}

/**
 * Strip markdown syntax, code blocks, tags, and emojis for speech synthesis (TTS).
 */
export function stripMarkdownForSpeech(text: string): string {
  if (!text) return '';

  let cleaned = text;

  // 1. Remove thinking / reasoning blocks entirely
  cleaned = cleaned.replace(
    /<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>([\s\S]*?)(?:<\/(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>|$)/gi,
    ''
  );

  // 2. Remove details / summary blocks
  cleaned = cleaned.replace(/<details[^>]*>[\s\S]*?<\/details>/gi, '');

  // 3. Remove code blocks ``` ... ```
  cleaned = cleaned.replace(/```[\s\S]*?```/g, '');

  // 4. Inline code `code` -> code
  cleaned = cleaned.replace(/`([^`]+)`/g, '$1');

  // 5. Remove HTML tags
  cleaned = cleaned.replace(/<[^>]+>/g, '');

  // 6. Image tags ![alt](url) -> alt
  cleaned = cleaned.replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1');

  // 7. Links [text](url) -> text
  cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

  // 8. Headers #, ##
  cleaned = cleaned.replace(/^\s*#+\s*/gm, '');

  // 9. Bold / italics
  cleaned = cleaned.replace(/\*{1,3}(.*?)\*{1,3}/g, '$1');
  cleaned = cleaned.replace(/_{1,3}(.*?)_{1,3}/g, '$1');
  cleaned = cleaned.replace(/~~(.*?)~~/g, '$1');

  // 10. Blockquotes
  cleaned = cleaned.replace(/^\s*>\s*/gm, '');

  // 11. Lists
  cleaned = cleaned.replace(/^\s*[-*+]\s+/gm, '');
  cleaned = cleaned.replace(/^\s*\d+\.\s+/gm, '');

  // 12. Horizontal rules
  cleaned = cleaned.replace(/^\s*[-*_]{3,}\s*$/gm, '');

  // 13. Stray symbols
  cleaned = cleaned.replace(/[#*_~`]+/g, '');

  // 14. Emojis and miscellaneous symbols
  cleaned = cleaned.replace(
    /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu,
    ''
  );

  // 15. Clean spaces and punctuation spacing
  cleaned = cleaned.replace(/[ \t]+/g, ' ');
  cleaned = cleaned.replace(/\s+([,.?!;:])/g, '$1');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  return cleaned.trim();
}
