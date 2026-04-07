"use client";

import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { MESSAGES } from "@/lib/constants/ui";

type Variant = "danger" | "primary";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  confirmVariant?: Variant;
  loading?: boolean;
}

export function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = MESSAGES.buttons.confirm,
  confirmVariant = "danger",
  loading = false,
}: Props) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            {MESSAGES.buttons.cancel}
          </Button>
          <Button
            variant={confirmVariant}
            size="sm"
            loading={loading}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-[var(--color-text)]">{description}</p>
    </Modal>
  );
}
