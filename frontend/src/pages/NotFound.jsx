import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import Button from '../components/ui/Button'

export default function NotFound() {
  return (
    <motion.div
      style={{ display: 'grid', placeItems: 'center', textAlign: 'center', padding: '10vh 0', gap: 16 }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="gradient-text" style={{ fontFamily: 'var(--display)', fontSize: 88, fontWeight: 700, lineHeight: 1 }}>
        404
      </div>
      <p className="muted">This page wandered off the ledger.</p>
      <Link to="/">
        <Button variant="outline">Back to dashboard</Button>
      </Link>
    </motion.div>
  )
}
