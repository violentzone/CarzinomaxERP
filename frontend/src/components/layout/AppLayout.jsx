import { useState } from 'react'
import { Outlet, useLocation, useMatches } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Menu, Sun, Moon, MessageSquare } from 'lucide-react'
import Sidebar from './Sidebar'
import ChatPanel from '../chat/ChatPanel'
import { useTheme } from '../../lib/useTheme'
import { pageVariants } from '../../lib/motion'

/**
 * Authenticated app shell: sidebar + topbar + animated routed content. The
 * topbar title comes from the active route's `handle.title`.
 */
export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const { theme, toggle } = useTheme()
  const location = useLocation()
  const matches = useMatches()
  const title = [...matches].reverse().find((m) => m.handle?.title)?.handle?.title || 'Dashboard'

  return (
    <div className="app-shell">
      <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
      {menuOpen && <div className="scrim" onClick={() => setMenuOpen(false)} />}

      <div className="main-col">
        <header className="topbar">
          <div className="row gap-3">
            <button className="icon-btn menu-btn" onClick={() => setMenuOpen(true)} aria-label="Menu">
              <Menu size={20} />
            </button>
            <span className="topbar-title">{title}</span>
          </div>
          <div className="topbar-actions">
            <button className="chat-toggle" onClick={() => setChatOpen(true)} aria-label="Chat" title="Assistant">
              <MessageSquare size={18} />
            </button>
            <button className="theme-toggle" onClick={toggle} aria-label="Toggle theme">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        <main className="page-scroll">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
