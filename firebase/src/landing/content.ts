// Public portfolio content. Taken from the reviewed entries in livekit/facts/lee.yaml,
// so it says no more than the avatar may. Keep the two in step.

export type Project = { name: string; url?: string; role?: string; description?: string; tags?: string[] }
export type Role = { title: string; org: string; dates: string; description: string }
export type Education = { title: string; org: string; detail?: string }

export const INTRO = {
  role: 'Senior software engineer',
  summary:
    'I build full-stack software and AI integrations, working directly with the people who use it. Before engineering, I spent six years teaching, and I still teach part time.',
}

export const PROJECTS: Project[] = [
  {
    name: 'Schooliki',
    url: 'https://schooliki.com',
    role: 'Founder and sole engineer, 2022 – present',
    description:
      'An AI-powered K–12 language-learning platform for English, Spanish, Portuguese and French. I run the whole loop: talking with educators, design, build, deploy and support. In beta.',
    tags: ['React', 'Vite', 'Firebase', 'Python', 'GCP', 'Claude', 'Gemini'],
  },
  {
    name: 'Awesome Aussie Possum Posse',
    url: 'https://awesomeaussiepossumposse.com',
  },
  {
    name: 'This site’s AI avatar',
    role: 'Invite only',
    description:
      'A voice and video avatar that answers questions about my work, only from facts I have reviewed. It always says it is an AI, and sends anything about offers or availability to me.',
    tags: ['LiveKit', 'Tavus', 'ElevenLabs', 'Gemini', 'FastAPI', 'React'],
  },
]

export const EXPERIENCE: Role[] = [
  {
    title: 'Senior Software Engineer',
    org: 'Lockheed Martin',
    dates: 'June 2021 – present',
    description:
      'Scope, prototype and ship analysis software with analysts and program engineers. Built a React platform for 3D model requests with role-based access, and C++ and Python data pipelines for real-time analytics.',
  },
  {
    title: 'Adjunct Professor',
    org: 'Antelope Valley College',
    dates: 'Aug 2024 – present',
    description: 'Teach computer applications and ESL.',
  },
  {
    title: 'Computer Scientist',
    org: 'JT4',
    dates: 'Feb 2020 – June 2021',
    description:
      'Built .NET, C# and Oracle applications for government test-range workflows, and led a legacy system migration in a live environment.',
  },
  {
    title: 'Software Engineer',
    org: 'Integrits Corporation',
    dates: 'Jan 2019 – Feb 2020',
    description: 'Modernized client applications and built SharePoint extensions for internal teams.',
  },
  {
    title: 'Magnet Coordinator and Lead Teacher',
    org: 'LAUSD',
    dates: '2013 – 2019',
    description:
      'Worked with parents, district leadership, partners and vendors, and shipped a seating-chart app integrated with Schoology on Google App Engine.',
  },
]

export const EDUCATION: Education[] = [
  { title: 'M.A. in TESOL', org: 'Cal State LA' },
  { title: 'B.A. in Communication', org: 'CSUN' },
  { title: 'Programming Certificate', org: 'West LA College' },
]

export const CERTIFICATIONS: Education[] = [
  { title: 'AI for Education (Advanced)', org: 'Kennesaw State University', detail: '2025' },
  { title: 'Google for Education, Level 2', org: 'Google' },
]
