import { motion } from 'framer-motion'
import Spinner from './Spinner'

/**
 * Animated button. Variants: primary | ghost | subtle | danger | outline.
 * Pass `loading` to show a spinner and disable, `icon` for a leading icon.
 */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon: Icon,
  className = '',
  type = 'button',
  disabled,
  ...rest
}) {
  return (
    <motion.button
      type={type}
      className={`btn btn-${variant} btn-${size} ${className}`}
      disabled={disabled || loading}
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      {...rest}
    >
      {loading ? <Spinner size={16} /> : Icon ? <Icon size={size === 'sm' ? 15 : 17} /> : null}
      {children && <span>{children}</span>}
    </motion.button>
  )
}
