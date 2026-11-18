import type { CallEnd } from './call-screen'
import { Button } from '@/components/ui/button'
import { LINKEDIN_URL } from '@/lib/config'
import { PageHeader, VisitorPage } from './layout'

export type EndReason = CallEnd | 'mic-denied'

const COPY: Record<EndReason, { title: string; body: string }> = {
  user: {
    title: 'Thanks for talking with Lee’s avatar',
    body: 'The call has ended and the transcript is saved for Lee to review. Anything the avatar said should be confirmed with Lee directly.',
  },
  'time-limit': {
    title: 'Time’s up',
    body: 'The call reached its time limit and has ended. The transcript is saved for Lee to review.',
  },
  'connection-lost': {
    title: 'The connection was lost',
    body: 'The call dropped before it finished. This used one of the sessions on your invite. Anything said before the drop is saved.',
  },
  'mic-denied': {
    title: 'We couldn’t use your microphone',
    body: 'The avatar needs your microphone to hear you. This attempt used one of the sessions on your invite. Allow microphone access in your browser settings, then reload the page and enter your code again if you have sessions left.',
  },
}

export function EndScreen({ reason }: { reason: EndReason }) {
  const { title, body } = COPY[reason]
  return (
    <VisitorPage>
      <PageHeader title={title}>
        <p>{body}</p>
      </PageHeader>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button asChild size="lg">
          <a href="/">Back to Lee’s home page</a>
        </Button>
        <Button asChild size="lg" variant="outline">
          <a href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer">
            Message Lee on LinkedIn
          </a>
        </Button>
      </div>
      <p className="text-muted-foreground">
        To reach the real Lee, or to ask for another session, message Lee on LinkedIn.
      </p>
    </VisitorPage>
  )
}
