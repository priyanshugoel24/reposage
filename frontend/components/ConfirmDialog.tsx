"use client";

import Modal from "@/components/Modal";

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  destructive?: boolean;
  isConfirming?: boolean;
  errorMessage?: string | null;
}

export default function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  destructive = false,
  isConfirming = false,
  errorMessage = null,
}: ConfirmDialogProps) {
  return (
    <Modal onClose={onCancel} title={title} maxWidthClassName="max-w-sm" showCloseButton={false}>
      <p className="text-sm text-text-secondary">{message}</p>

      {errorMessage && <p className="mt-3 text-sm text-danger">{errorMessage}</p>}

      <div className="mt-6 flex items-center justify-end gap-4">
        <button
          type="button"
          onClick={onCancel}
          disabled={isConfirming}
          className="font-mono text-sm text-text-secondary hover:text-text-primary disabled:opacity-60"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isConfirming}
          className={`rounded-md px-4 py-2 font-mono text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60 ${
            destructive
              ? "bg-danger text-danger-foreground hover:brightness-110"
              : "bg-accent text-accent-foreground hover:bg-accent-strong"
          }`}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
