import { Routes, Route, NavLink, Link } from 'react-router-dom'
import { SITE } from './config'
import Home from './pages/Home'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import About from './pages/About'
import Contact from './pages/Contact'

const navLink = ({ isActive }: { isActive: boolean }) =>
  `text-sm transition-colors hover:text-fg ${isActive ? 'text-fg' : 'text-muted'}`

function Nav() {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
      <nav className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
        <Link to="/" className="font-mono text-sm text-fg">
          {SITE.name.toLowerCase().replace(/\s+/g, '_')}
          <span className="text-accent">.</span>
        </Link>
        <div className="flex gap-6">
          <NavLink to="/projects" className={navLink}>projects</NavLink>
          <NavLink to="/about" className={navLink}>about</NavLink>
          <NavLink to="/contact" className={navLink}>contact</NavLink>
        </div>
      </nav>
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-24 border-t border-border">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-8 text-sm text-muted">
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
  return (
    <div className="flex min-h-screen flex-col">
      <Nav />
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:slug" element={<ProjectDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/contact" element={<Contact />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
