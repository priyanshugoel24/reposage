"use client";

import { ReactNode } from "react";

interface ModalProps {
  onClose: () => void;
  title: string;
  children: ReactNode;
  maxWidthClassName?: string;
  showCloseButton?: boolean;
}

export default function Modal({
  onClose,
  title,
  children,
  maxWidthClassName = "max-w-md",
  showCloseButton = true,
}: ModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div
        className={`w-full ${maxWidthClassName} rounded-lg border border-border-strong bg-bg-inset p-6 shadow-2xl`}
      >
        <div className="mb-6 flex items-center justify-between gap-4">
          <h2 className="text-lg font-bold text-text-primary">{title}</h2>
          {showCloseButton && (
            <button
              type="button"
              onClick={onClose}
              className="text-text-muted hover:text-text-primary"
              aria-label="Close"
            >
              ×
            </button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}
