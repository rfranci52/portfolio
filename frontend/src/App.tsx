import { useEffect } from 'react'
import { Routes, Route, NavLink, Link, useLocation, useNavigationType } from 'react-router-dom'
import { SITE } from './config'
import { useTracker } from './chat/useTracker'
import ChatWidget from './components/ChatWidget'
import Home from './pages/Home'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import HowThisWorks from './pages/HowThisWorks'
import About from './pages/About'
import Contact from './pages/Contact'

const navLink = ({ isActive }: { isActive: boolean }) =>
  `text-[13px] transition-colors hover:text-fg sm:text-sm ${isActive ? 'text-fg' : 'text-muted'}`

function Nav() {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
      <nav className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-x-4 gap-y-1 px-6 py-4">
        <Link to="/" className="font-mono text-sm text-fg">
          {SITE.name.toLowerCase().replace(/\s+/g, '_')}
          <span className="text-accent">.</span>
        </Link>
        <div className="flex gap-3 sm:gap-6">
          <NavLink to="/projects" className={navLink}>projects</NavLink>
          <NavLink to="/how-this-works" className={navLink}>how this works</NavLink>
          <NavLink to="/contact" className={navLink}>contact</NavLink>
        </div>
      </nav>
    </header>
  )
}

function Footer({ docked }: { docked: boolean }) {
  return (
    <footer className="mt-24 border-t border-border">
      <div className={`mx-auto flex max-w-3xl items-center justify-between gap-4 px-6 pt-8 text-sm text-muted ${docked ? 'pb-20' : 'pb-8'}`}>
        <span>© {new Date().getFullYear()} {SITE.name}</span>
        <div className="flex gap-5 font-mono">
          {SITE.linkedin && (
            <a href={SITE.linkedin} target="_blank" rel="noreferrer" className="hover:text-fg">linkedin</a>
          )}
          {SITE.github && (
            <a href={SITE.github} target="_blank" rel="noreferrer" className="hover:text-fg">github</a>
          )}
          <Link to="/contact" className="hover:text-fg">email</Link>
        </div>
      </div>
    </footer>
  )
}

export default function App() {
  const { pathname } = useLocation()
  const navigationType = useNavigationType()
  useTracker()

  // Links in chat answers change the page, so a new page starts at the top.
  // Back and forward keep the browser's own scroll restoration.
  useEffect(() => {
    if (navigationType !== 'POP') window.scrollTo(0, 0)
  }, [pathname, navigationType])

  const home = pathname === '/'

  return (
    <div className="flex min-h-screen flex-col">
      <Nav />
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:slug" element={<ProjectDetail />} />
          <Route path="/how-this-works" element={<HowThisWorks />} />
          <Route path="/about" element={<About />} />
          <Route path="/contact" element={<Contact />} />
        </Routes>
      </main>
      <Footer docked={!home} />
      {!home && <ChatWidget />}
    </div>
  )
}
