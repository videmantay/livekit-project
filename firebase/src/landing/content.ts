// Public portfolio content. Taken from the reviewed entries in livekit/facts/lee.yaml,
// so it says no more than the avatar may. Keep the two in step.
//
// Each piece of text holds all three languages side by side, so a change in one is hard
// to miss in the others. A plain string (names, job titles, product names) is the same
// in every language. Spanish and Portuguese are written in gender-neutral forms.

export const LOCALES = ['en', 'es', 'pt'] as const
export type Locale = (typeof LOCALES)[number]

type Localized = Record<Locale, string>
export type Text = string | Localized

export function tr(text: Text, locale: Locale): string {
  return typeof text === 'string' ? text : text[locale]
}

// The landing page lives at / (English), /es and /pt. The invite flow stays English (ADR-17).
export const LOCALE_PATHS: Record<Locale, string> = { en: '/', es: '/es', pt: '/pt' }

export function localeFromPath(path: string): Locale | null {
  const match = LOCALES.find((l) => l !== 'en' && LOCALE_PATHS[l] === path)
  return match ?? (path === '/' ? 'en' : null)
}

export const LANGUAGE_NAMES: Record<Locale, string> = { en: 'English', es: 'Español', pt: 'Português' }

export type Project = {
  name: Text
  url?: string
  youtube?: string
  role?: Text
  description?: Text
  tags?: string[]
}
export type Channel = { name: string; url: string; language: Locale }
export type Role = { title: Text; org: string; dates: Text; description: Text }
export type Education = { title: Text; org: string; detail?: string }

const UI_EN = {
  nav: { label: 'Main', projects: 'Projects', channels: 'Channels', experience: 'Experience', education: 'Education' },
  languageLabel: 'Language',
  invite: 'I have an invite',
  inviteShort: 'Invite',
  heading: "I'm Lee, a senior software engineer",
  summary:
    'I build full-stack software and AI integrations, working directly with the people who use it. Before engineering, I spent six years teaching, and I still teach part time.',
  jumpToProjects: 'Jump to projects',
  aboutTitle: 'About me',
  aboutBody: 'Full-stack software and AI integrations, built with the people who use them.',
  aboutLink: 'My experience',
  avatarTitle: 'Talk to my AI avatar',
  avatarBody: 'Have an invite code? Ask my AI avatar about my work, by voice. No code? Ask me on LinkedIn.',
  avatarLink: 'Enter invite code',
  followTitle: 'Follow me',
  youtubeChannel: 'YouTube channel',
  channelsTitle: 'YouTube channels',
  inLanguage: { en: 'In English', es: 'In Spanish', pt: 'In Portuguese' } as Record<Locale, string>,
  certifications: 'Certifications',
}
type UiStrings = typeof UI_EN

export const UI: Record<Locale, UiStrings> = {
  en: UI_EN,
  es: {
    nav: { label: 'Principal', projects: 'Proyectos', channels: 'Canales', experience: 'Experiencia', education: 'Formación' },
    languageLabel: 'Idioma',
    invite: 'Tengo una invitación',
    inviteShort: 'Invitación',
    heading: 'Soy Lee y creo software',
    summary:
      'Desarrollo software full-stack e integraciones de IA, en contacto directo con las personas que lo usan. Antes de dedicarme a la ingeniería, pasé seis años en la docencia, y sigo dando clases a tiempo parcial.',
    jumpToProjects: 'Ir a proyectos',
    aboutTitle: 'Sobre mí',
    aboutBody: 'Software full-stack e integraciones de IA, creados junto a quienes los usan.',
    aboutLink: 'Mi experiencia',
    avatarTitle: 'Habla con mi avatar de IA',
    avatarBody:
      '¿Tienes un código de invitación? Pregúntale a mi avatar de IA sobre mi trabajo, por voz. Por ahora, la llamada es en inglés. ¿No tienes código? Escríbeme por LinkedIn.',
    avatarLink: 'Introducir código',
    followTitle: 'Sígueme',
    youtubeChannel: 'Canal de YouTube',
    channelsTitle: 'Canales de YouTube',
    inLanguage: { en: 'En inglés', es: 'En español', pt: 'En portugués' },
    certifications: 'Certificaciones',
  },
  pt: {
    nav: { label: 'Principal', projects: 'Projetos', channels: 'Canais', experience: 'Experiência', education: 'Formação' },
    languageLabel: 'Idioma',
    invite: 'Tenho um convite',
    inviteShort: 'Convite',
    heading: 'Sou Lee e crio software',
    summary:
      'Desenvolvo software full-stack e integrações de IA, trabalhando diretamente com as pessoas que o usam. Antes da engenharia, passei seis anos dando aula, e ainda dou aulas em meio período.',
    jumpToProjects: 'Ir para projetos',
    aboutTitle: 'Sobre mim',
    aboutBody: 'Software full-stack e integrações de IA, criados com quem os usa.',
    aboutLink: 'Minha experiência',
    avatarTitle: 'Converse com meu avatar de IA',
    avatarBody:
      'Tem um código de convite? Pergunte ao meu avatar de IA sobre o meu trabalho, por voz. Por enquanto, a chamada é em inglês. Não tem código? Fale comigo no LinkedIn.',
    avatarLink: 'Inserir código',
    followTitle: 'Siga-me',
    youtubeChannel: 'Canal no YouTube',
    channelsTitle: 'Canais do YouTube',
    inLanguage: { en: 'Em inglês', es: 'Em espanhol', pt: 'Em português' },
    certifications: 'Certificações',
  },
}

export const PROJECTS: Project[] = [
  {
    name: 'Schooliki',
    url: 'https://schooliki.com',
    role: {
      en: 'Founder and sole engineer, 2022 – present',
      es: 'Fundado y desarrollado por mí, 2022 – actualidad',
      pt: 'Fundado e desenvolvido por mim, 2022 – presente',
    },
    description: {
      en: 'An AI-powered K–12 language-learning platform for English, Spanish, Portuguese and French. I run the whole loop: talking with educators, design, build, deploy and support. In beta.',
      es: 'Una plataforma de aprendizaje de idiomas con IA para primaria y secundaria (K–12), para inglés, español, portugués y francés. Me encargo de todo el ciclo: hablar con docentes, diseño, desarrollo, despliegue y soporte. En beta.',
      pt: 'Uma plataforma de aprendizado de idiomas com IA para o ensino básico (K–12), para inglês, espanhol, português e francês. Cuido de todo o ciclo: conversar com docentes, design, desenvolvimento, implantação e suporte. Em beta.',
    },
    tags: ['React', 'Mantine','Firebase', 'Python', 'FastAPI', 'GCP', 'Claude', 'Gemini'],
  },
  {
    name: 'Awesome Aussie Possum Posse',
    url: 'https://awesomeaussiepossumposse.com',
    youtube: 'https://www.youtube.com/@awesausspossposs',
    role:{
      en: 'Author and Media Engineer, 2023 – present',
      es: 'Autor e ingeniero de medios, 2023 – actualidad',
      pt: 'Autor e engenheiro de mídia, 2023 – presente',
    },
    description: {
      en: 'A children’s book and YouTube channel about how a group of seven Aussie possums helped shape the Wild West. I wrote it with my daughter, and contracted an illustrator. I built the website and I manage the YouTube channel.',
      es: 'Un libro y canal de YouTube sobre cómo un grupo de siete zarigüeyas australianas ayudaron a moldear el Oeste Salvaje. Lo escribí con mi hija y contraté a un ilustrador. Construí el sitio web y gestiono el canal de YouTube.',
      pt: 'Um livro e canal do YouTube sobre como um grupo de sete gambás australianas ajudaram a moldar o Oeste Selvagem. Escrevi-o com minha filha e contratei um ilustrador. Construí o site e gerencio o canal do YouTube.'
    },
    tags: ['React', 'Mantine','Firebase', 'GCP', 'Claude' , 'Adobe Illustrator', 'Adobe Photoshop', 'Adobe Animate'],
  },
  {
    name: { en: 'This site’s AI avatar', es: 'El avatar de IA de este sitio', pt: 'O avatar de IA deste site' },
    role: { en: 'Invite only', es: 'Solo con invitación', pt: 'Somente com convite' },
    description: {
      en: 'A voice and video avatar that answers questions about my work, only from facts I have reviewed. It always says it is an AI, and sends anything about offers or availability to me.',
      es: 'Un avatar de voz y video que responde preguntas sobre mi trabajo, solo con datos que he revisado. Siempre dice que es una IA y me deja a mí todo lo relacionado con ofertas o disponibilidad. Por ahora habla en inglés.',
      pt: 'Um avatar de voz e vídeo que responde perguntas sobre o meu trabalho, apenas com fatos que eu revisei. Sempre diz que é uma IA e deixa comigo tudo sobre propostas ou disponibilidade. Por enquanto, fala em inglês.',
    },
    tags: ['LiveKit', 'Tavus', 'ElevenLabs', 'Gemini', 'FastAPI', 'React'],
  },
]

// Names and languages only, until Lee writes a line for each.
export const CHANNELS: Channel[] = [
  { name: 'Aprendizaje Codificado', url: 'https://www.youtube.com/@AprendizajeCodificado', language: 'es' },
  { name: 'Aprendizagem Codificada', url: 'https://www.youtube.com/@AprendizagemCodificada', language: 'pt' },
  { name: 'Lessen Planning ESL', url: 'https://www.youtube.com/@LessenPlanning-ESL', language: 'en' },
]

// Job titles stay in English, as the employers gave them.
export const EXPERIENCE: Role[] = [
  {
    title: 'Senior Software Engineer',
    org: 'Lockheed Martin',
    dates: { en: 'June 2021 – present', es: 'junio 2021 – actualidad', pt: 'junho de 2021 – presente' },
    description: {
      en: 'Scope, prototype and ship analysis software with analysts and program engineers. Built a React platform for 3D model requests with role-based access, and C++ and Python data pipelines for real-time analytics.',
      es: 'Defino, prototipo y entrego software de análisis junto a analistas y el equipo de ingeniería del programa. Creé una plataforma en React para solicitudes de modelos 3D con acceso por roles, y pipelines de datos en C++ y Python para analítica en tiempo real.',
      pt: 'Defino o escopo, prototipo e entrego software de análise com analistas e a equipe de engenharia do programa. Criei uma plataforma em React para solicitações de modelos 3D com acesso por perfil, e pipelines de dados em C++ e Python para análises em tempo real.',
    },
  },
  {
    title: 'Adjunct Professor',
    org: 'Antelope Valley College',
    dates: { en: 'Aug 2024 – present', es: 'agosto 2024 – actualidad', pt: 'agosto de 2024 – presente' },
    description: {
      en: 'Teach computer applications and ESL.',
      es: 'Enseño aplicaciones informáticas e inglés como segunda lengua (ESL).',
      pt: 'Ensino aplicativos de informática e inglês como segunda língua (ESL).',
    },
  },
  {
    title: 'Computer Scientist',
    org: 'JT4',
    dates: {
      en: 'Feb 2020 – June 2021',
      es: 'febrero 2020 – junio 2021',
      pt: 'fevereiro de 2020 – junho de 2021',
    },
    description: {
      en: 'Built .NET, C# and Oracle applications for government test-range workflows, and led a legacy system migration in a live environment.',
      es: 'Desarrollé aplicaciones en .NET, C# y Oracle para los procesos de campos de pruebas del gobierno, y lideré la migración de un sistema heredado en un entorno en producción.',
      pt: 'Desenvolvi aplicações em .NET, C# e Oracle para os processos de campos de teste do governo, e liderei a migração de um sistema legado em ambiente de produção.',
    },
  },
  {
    title: 'Software Engineer',
    org: 'Integrits Corporation',
    dates: {
      en: 'Jan 2019 – Feb 2020',
      es: 'enero 2019 – febrero 2020',
      pt: 'janeiro de 2019 – fevereiro de 2020',
    },
    description: {
      en: 'Modernized client applications and built SharePoint extensions for internal teams.',
      es: 'Modernicé aplicaciones de clientes y creé extensiones de SharePoint para equipos internos.',
      pt: 'Modernizei aplicações de clientes e criei extensões do SharePoint para equipes internas.',
    },
  },
  {
    title: 'Magnet Coordinator and Lead Teacher',
    org: 'LAUSD',
    dates: '2013 – 2019',
    description: {
      en: 'Worked with parents, district leadership, partners and vendors, and shipped a seating-chart app integrated with Schoology on Google App Engine.',
      es: 'Trabajé con familias, la dirección del distrito, socios y proveedores, y lancé una app de distribución del aula integrada con Schoology en Google App Engine.',
      pt: 'Trabalhei com famílias, a direção do distrito, parceiros e fornecedores, e lancei um app de mapa de sala integrado ao Schoology no Google App Engine.',
    },
  },
]

export const EDUCATION: Education[] = [
  {
    title: { en: 'M.A. in TESOL', es: 'Maestría (M.A.) en TESOL', pt: 'Mestrado (M.A.) em TESOL' },
    org: 'Cal State LA',
  },
  {
    title: {
      en: 'B.A. in Communication',
      es: 'Licenciatura (B.A.) en Comunicación',
      pt: 'Bacharelado (B.A.) em Comunicação',
    },
    org: 'CSUN',
  },
  {
    title: { en: 'Programming Certificate', es: 'Certificado en Programación', pt: 'Certificado em Programação' },
    org: 'West LA College',
  },
]

// Certificate names stay as issued.
export const CERTIFICATIONS: Education[] = [
  {
    title: 'AI for Education (Advanced)',
    org: 'Kennesaw State University',
    detail: '2025',
  },
  { title: 'Google for Education, Level 2', org: 'Google' },
]
