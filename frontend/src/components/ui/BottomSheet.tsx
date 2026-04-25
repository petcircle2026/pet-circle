'use client';

import { useScrollLock } from '@/hooks/useScrollLock';
import { BUTTONS } from '@/lib/css-classes';
import { ARIA_LABELS } from '@/lib/aria-labels';

interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export default function BottomSheet({ open, onClose, title, children }: BottomSheetProps) {
  useScrollLock(open);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center animate-fadeIn">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="bottom-sheet">
        {/* Drag handle */}
        <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />

        {/* Header row: title + close button inline */}
        <div className="bottom-sheet-header">
          {title ? <h3 className="bottom-sheet-title">{title}</h3> : <span />}
          <button
            type="button"
            onClick={onClose}
            className={BUTTONS.close}
            aria-label={ARIA_LABELS.close}
          >
            &times;
          </button>
        </div>

        {children}
      </div>
    </div>
  );
}
