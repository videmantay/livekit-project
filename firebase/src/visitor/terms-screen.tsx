import { useState } from 'react'
import { TermsText } from '@/components/terms-text'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { ApiError, type Terms } from '@/lib/api'
import { MAX_SESSION_MINUTES } from '@/lib/config'
import { TERMS_LANGUAGE_NAMES, type TermsLanguage } from '@/lib/terms-language'
import { PageHeader, VisitorPage } from './layout'

// The checkbox label is part of the consent, so it's translated with the terms and reviewed
// with them (ADR-20).
const TEXT: Record<
  TermsLanguage,
  {
    eyebrow: string
    title: string
    intro: string
    changed: string
    callLength: (minutes: number) => string
    agree: string
    continue: string
    language: string
    switchFailed: string
    tooMany: string
  }
> = {
  en: {
    eyebrow: 'Step 1 of 2',
    title: 'Before you start',
    intro: 'Please read how the conversation works and what is kept.',
    changed: 'The terms have changed since you opened this page. Please read them again.',
    callLength: (minutes) =>
      `Calls last up to ${minutes} minutes. Your microphone is only requested after you agree and start the call.`,
    agree: 'I have read this and agree to my conversation being transcribed, stored and reviewed as described.',
    continue: 'Continue',
    language: 'Language of the terms',
    switchFailed: "Couldn't change the language. Please try again.",
    tooMany: 'Too many attempts. Please wait a minute and try again.',
  },
  es: {
    eyebrow: 'Paso 1 de 2',
    title: 'Antes de empezar',
    intro: 'Lea cómo funciona la conversación y qué se guarda.',
    changed: 'Las condiciones han cambiado desde que abrió esta página. Léalas de nuevo.',
    callLength: (minutes) =>
      `Las llamadas duran hasta ${minutes} minutos. El micrófono solo se solicita después de que acepte e inicie la llamada.`,
    agree: 'He leído esto y acepto que mi conversación se transcriba, se almacene y se revise como se describe.',
    continue: 'Continuar',
    language: 'Idioma de las condiciones',
    switchFailed: 'No se pudo cambiar el idioma. Inténtelo de nuevo.',
    tooMany: 'Demasiados intentos. Espere un minuto y vuelva a intentarlo.',
  },
}

export function TermsScreen({
  terms,
  termsChanged,
  onSwitchLanguage,
  onAccept,
}: {
  terms: Terms
  termsChanged?: boolean
  onSwitchLanguage: (language: TermsLanguage) => Promise<void>
  onAccept: () => void
}) {
  // Always starts unticked, including after a 409 reload or a language switch (I2, I3).
  const [agreed, setAgreed] = useState(false)
  const [switching, setSwitching] = useState(false)
  const [switchError, setSwitchError] = useState<string>()
  const text = TEXT[terms.language]

  async function switchTo(language: TermsLanguage) {
    setSwitching(true)
    setSwitchError(undefined)
    try {
      await onSwitchLanguage(language)
    } catch (err) {
      setSwitchError(err instanceof ApiError && err.status === 429 ? text.tooMany : text.switchFailed)
      setSwitching(false)
    }
  }

  return (
    <VisitorPage>
      <div lang={terms.language} className="contents">
        {/* Only when cloud-run offers another language, so English-only visitors see no change. */}
        {terms.offered.length > 1 && (
          <ul className="flex flex-wrap gap-2" aria-label={text.language}>
            {terms.offered.map((language) => (
              <li key={language}>
                <Button
                  variant={language === terms.language ? 'secondary' : 'ghost'}
                  size="sm"
                  lang={language}
                  aria-pressed={language === terms.language}
                  disabled={switching || language === terms.language}
                  onClick={() => void switchTo(language)}
                >
                  {TERMS_LANGUAGE_NAMES[language]}
                </Button>
              </li>
            ))}
          </ul>
        )}

        <PageHeader eyebrow={text.eyebrow} title={text.title}>
          <p>{text.intro}</p>
        </PageHeader>

        {(termsChanged || switchError) && (
          <p role="alert" className="rounded-lg border border-foreground/20 bg-muted px-4 py-3">
            {switchError ?? text.changed}
          </p>
        )}

        <Card>
          <CardContent className="max-h-[50vh] overflow-y-auto">
            <TermsText text={terms.text} />
          </CardContent>
        </Card>

        <p className="text-muted-foreground">{text.callLength(MAX_SESSION_MINUTES)}</p>

        <div className="flex items-start gap-3">
          <Checkbox id="agree" checked={agreed} onCheckedChange={(v) => setAgreed(v === true)} className="mt-1" />
          <Label htmlFor="agree" className="text-base/snug font-normal">
            {text.agree}
          </Label>
        </div>

        <div>
          <Button size="lg" disabled={!agreed || switching} onClick={onAccept}>
            {text.continue}
          </Button>
        </div>
      </div>
    </VisitorPage>
  )
}
