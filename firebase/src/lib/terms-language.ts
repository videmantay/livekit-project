// Languages the terms can be written in. cloud-run says which are offered right now; Spanish
// stays off there until its text is reviewed (ADR-20).
export const TERMS_LANGUAGES = ['en', 'es'] as const
export type TermsLanguage = (typeof TERMS_LANGUAGES)[number]

export const TERMS_LANGUAGE_NAMES: Record<TermsLanguage, string> = { en: 'English', es: 'Español' }

export function isTermsLanguage(value: unknown): value is TermsLanguage {
  return TERMS_LANGUAGES.includes(value as TermsLanguage)
}

/**
 * The first language in the browser's preference order that the terms come in, else English.
 * Only a starting point: the terms screen has a switch, and nothing about the choice is stored.
 */
export function preferredTermsLanguage(
  languages: readonly string[] = typeof navigator === 'undefined' ? [] : navigator.languages,
): TermsLanguage {
  for (const tag of languages) {
    const primary = tag.toLowerCase().split('-')[0]
    if (isTermsLanguage(primary)) return primary
  }
  return 'en'
}
