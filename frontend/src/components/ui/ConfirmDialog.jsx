import Modal from './Modal'
import Button from './Button'

/**
 * Confirmation modal for destructive actions.
 *
 * Props:
 *  - open, onClose
 *  - onConfirm: called when the user confirms
 *  - title, message: what is about to happen
 *  - hint: optional extra consequence line (muted)
 *  - confirmLabel: button text (default "Delete")
 *  - loading: disables buttons and spins the confirm button
 */
export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  message,
  hint,
  confirmLabel = 'Delete',
  loading = false,
}) {
  return (
    <Modal
      open={open}
      onClose={loading ? undefined : onClose}
      title={title}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="col gap-2">
        {message && <p>{message}</p>}
        {hint && <p className="muted">{hint}</p>}
      </div>
    </Modal>
  )
}
