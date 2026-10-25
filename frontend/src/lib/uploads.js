/**
 * Upload limits shared by the chat composer and the Finance "Book from receipt"
 * button. The backend (`POST /chatbot/upload`, `POST /finance/receipt`,
 * `UPLOAD_MAX_BYTES`, `MAX_ATTACHMENTS`) enforces the same values.
 */
export const UPLOAD_ACCEPT = 'image/png,image/jpeg,image/webp,application/pdf'
export const UPLOAD_MAX_BYTES = 10 * 1024 * 1024
export const UPLOAD_MAX_FILES = 5
