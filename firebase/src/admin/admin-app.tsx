import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AccessCodesPage } from './access-codes-page'
import { ConversationsPage } from './conversations-page'
import { FactsPage } from './facts-page'

type Tab = 'conversations' | 'codes' | 'facts'

export function AdminApp() {
  // Mock sign-in. The real one uses Firebase Google sign-in, and cloud-run checks the
  // ID token and the one allowed account on every request (ADR-10, A3).
  const [signedIn, setSignedIn] = useState(false)
  const [tab, setTab] = useState<Tab>('conversations')
  const [factSeed, setFactSeed] = useState<{ question: string; key: number }>()

  if (!signedIn) {
    return (
      <main className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-16">
        <h1 className="text-3xl font-bold">Admin</h1>
        <p className="text-muted-foreground">This area is private. Only Lee's Google account can sign in.</p>
        <div>
          <Button size="lg" onClick={() => setSignedIn(true)}>
            Sign in with Google
          </Button>
        </div>
      </main>
    )
  }

  function addAsFact(question: string) {
    // Only the question is carried over, never who asked it (ADR-21).
    setFactSeed({ question, key: Date.now() })
    setTab('facts')
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold">Admin</h1>
        <Button variant="outline" onClick={() => setSignedIn(false)}>
          Sign out
        </Button>
      </header>

      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)} className="gap-6">
        <TabsList className="h-auto w-full flex-wrap justify-start border bg-muted sm:w-fit">
          <TabsTrigger value="conversations">Conversations</TabsTrigger>
          <TabsTrigger value="codes">Access codes</TabsTrigger>
          <TabsTrigger value="facts">Facts</TabsTrigger>
        </TabsList>
        <TabsContent value="conversations">
          <ConversationsPage onAddAsFact={addAsFact} />
        </TabsContent>
        <TabsContent value="codes">
          <AccessCodesPage />
        </TabsContent>
        <TabsContent value="facts">
          <FactsPage key={factSeed?.key} seed={factSeed?.question} />
        </TabsContent>
      </Tabs>
    </main>
  )
}
