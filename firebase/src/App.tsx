import { Mic, Phone } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

const SWATCHES = [
  'bg-background',
  'bg-card',
  'bg-secondary',
  'bg-input',
  'bg-foreground',
  'bg-muted-foreground',
  'bg-faint',
  'bg-brand',
  'bg-brand-subtle',
  'bg-destructive',
  'bg-success',
  'bg-visitor',
]

// Temporary style check. Replaced by the real screens.
export default function App() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-10 px-6 py-12">
      <header className="flex flex-col gap-4">
        <p className="text-sm tracking-[0.12em] text-brand uppercase">By invitation</p>
        <h1 className="text-[56px] leading-[1.04] font-bold tracking-[-0.02em]">
          Talk to my résumé.
        </h1>
        <p className="text-lg/relaxed text-muted-foreground">
          Enter the access code from your invitation.
        </p>
      </header>

      <form className="flex flex-col gap-3">
        <Label htmlFor="code">Access code</Label>
        <div className="flex flex-wrap gap-2.5">
          <Input
            id="code"
            placeholder="XXXX-XXXX-XXXX"
            className="h-14 flex-[1_1_240px] rounded-xl font-heading text-xl font-semibold tracking-[0.18em] uppercase md:text-xl"
          />
          <Button size="xl">Enter</Button>
        </div>
        <p role="alert" className="text-sm text-error">
          That code is invalid or has expired.
        </p>
      </form>

      <div className="flex flex-wrap items-center gap-3">
        <Button size="xl" data-icon="inline-start">
          <Mic />
          Start a conversation
        </Button>
        <Button variant="brand" size="lg">
          Email Lee
        </Button>
        <Button variant="outline" size="lg">
          Export
        </Button>
        <Button variant="danger" size="xl" className="rounded-full">
          End call
        </Button>
        <Button variant="outline" size="icon-xl" aria-label="Mute microphone">
          <Phone />
        </Button>
      </div>

      <ToggleGroup type="single" defaultValue="en" variant="pill" size="lg" aria-label="Language">
        <ToggleGroupItem value="en">English</ToggleGroupItem>
        <ToggleGroupItem value="es">Español</ToggleGroupItem>
        <ToggleGroupItem value="pt">Português</ToggleGroupItem>
      </ToggleGroup>

      <Tabs defaultValue="shared" className="max-w-sm">
        <TabsList className="w-full">
          <TabsTrigger value="shared">Shared (3)</TabsTrigger>
          <TabsTrigger value="transcript">Transcript</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card className="max-w-sm">
        <CardHeader>
          <p className="text-[13px] tracking-[0.08em] text-faint uppercase">Card label</p>
          <CardTitle className="font-heading text-[22px]">Card title</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-muted-foreground">
          <p>Body copy on a card surface.</p>
          <div className="flex gap-2">
            <Badge variant="brand">3</Badge>
            <Badge variant="secondary">voice AI</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="terms" />
            <Label htmlFor="terms">I agree</Label>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-6 gap-2">
        {SWATCHES.map((swatch) => (
          <div key={swatch} className={`h-12 rounded-md border ${swatch}`} title={swatch} />
        ))}
      </div>
    </main>
  )
}
