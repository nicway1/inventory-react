/**
 * ConfirmDialog Component
 *
 * A reusable confirmation dialog for destructive or important actions.
 * Built on top of the Modal component with specialized variants.
 */

import React, { Fragment, useCallback, useState } from 'react'
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Transition,
  TransitionChild,
} from '@headlessui/react'
import {
  ExclamationTriangleIcon,
  QuestionMarkCircleIcon,
  InformationCircleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'

// Dialog variants
export type ConfirmDialogVariant = 'default' | 'danger' | 'warning' | 'info'

export interface ConfirmDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean
  /** Callback when the dialog should close */
  onClose: () => void
  /** Callback when the action is confirmed */
  onConfirm: () => void | Promise<void>
  /** Dialog title */
  title: string
  /** Dialog description/message */
  description: string
  /** Variant style */
  variant?: ConfirmDialogVariant
  /** Confirm button text */
  confirmText?: string
  /** Cancel button text */
  cancelText?: string
  /** Whether the confirm action is loading */
  isLoading?: boolean
  /** Icon to display (overrides variant default) */
  icon?: React.ElementType
  /** Additional content to display */
  children?: React.ReactNode
}

// Variant configuration
const variantConfig: Record<
  ConfirmDialogVariant,
  {
    icon: React.ElementType
    iconBgClass: string
    iconClass: string
    confirmButtonClass: string
  }
> = {
  default: {
    icon: QuestionMarkCircleIcon,
    iconBgClass: 'bg-[#0176D3]/10',
    iconClass: 'text-[#0176D3]',
    confirmButtonClass:
      'bg-[#0176D3] hover:bg-[#014486] focus-visible:ring-[#0176D3]',
  },
  danger: {
    icon: TrashIcon,
    iconBgClass: 'bg-[#C23934]/10',
    iconClass: 'text-[#C23934]',
    confirmButtonClass:
      'bg-[#C23934] hover:bg-[#A61A14] focus-visible:ring-[#C23934]',
  },
  warning: {
    icon: ExclamationTriangleIcon,
    iconBgClass: 'bg-[#FE9339]/10',
    iconClass: 'text-[#B86E00]',
    confirmButtonClass:
      'bg-[#FE9339] hover:bg-[#DD7A14] focus-visible:ring-[#FE9339]',
  },
  info: {
    icon: InformationCircleIcon,
    iconBgClass: 'bg-[#0176D3]/10',
    iconClass: 'text-[#0176D3]',
    confirmButtonClass:
      'bg-[#0176D3] hover:bg-[#014486] focus-visible:ring-[#0176D3]',
  },
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  variant = 'default',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isLoading = false,
  icon: CustomIcon,
  children,
}: ConfirmDialogProps) {
  const [internalLoading, setInternalLoading] = useState(false)
  const config = variantConfig[variant]
  const Icon = CustomIcon || config.icon
  const loading = isLoading || internalLoading

  const handleConfirm = useCallback(async () => {
    try {
      setInternalLoading(true)
      await onConfirm()
      onClose()
    } catch (error) {
      // Let the caller handle errors
      console.error('Confirm action failed:', error)
    } finally {
      setInternalLoading(false)
    }
  }, [onConfirm, onClose])

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        {/* Backdrop */}
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm" />
        </TransitionChild>

        {/* Dialog container */}
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex items-center justify-center min-h-full p-4 text-center">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel className="relative w-full max-w-md transform overflow-hidden rounded bg-white text-left shadow-xl transition-all">
                <div className="p-6">
                  {/* Icon and content */}
                  <div className="flex items-start gap-4">
                    <div
                      className={cn(
                        'flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full',
                        config.iconBgClass
                      )}
                    >
                      <Icon
                        className={cn('w-6 h-6', config.iconClass)}
                        aria-hidden="true"
                      />
                    </div>
                    <div className="flex-1 pt-1">
                      <DialogTitle
                        as="h3"
                        className="text-lg font-semibold leading-6 text-gray-900"
                      >
                        {title}
                      </DialogTitle>
                      <p className="mt-2 text-sm text-gray-500">{description}</p>
                      {children && <div className="mt-4">{children}</div>}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 px-6 py-4 bg-[#F3F3F3] border-t border-[#DDDBDA]">
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={loading}
                    className={cn(
                      'inline-flex justify-center rounded px-6 py-3 text-sm font-semibold',
                      'text-[#0176D3] bg-white border border-[#0176D3]',
                      'hover:bg-[#F4F6F9] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0176D3]',
                      'disabled:opacity-50 disabled:cursor-not-allowed'
                    )}
                  >
                    {cancelText}
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirm}
                    disabled={loading}
                    className={cn(
                      'inline-flex justify-center items-center gap-2 rounded px-6 py-3 text-sm font-semibold text-white',
                      'shadow-[0_1px_3px_rgba(0,0,0,0.12)] hover:shadow-[0_2px_6px_rgba(0,0,0,0.16)]',
                      'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                      config.confirmButtonClass
                    )}
                  >
                    {loading && (
                      <svg
                        className="w-4 h-4 animate-spin"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                    )}
                    {confirmText}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

// Hook for managing confirm dialog state
export function useConfirmDialog() {
  const [state, setState] = useState<{
    isOpen: boolean
    title: string
    description: string
    variant: ConfirmDialogVariant
    confirmText: string
    cancelText: string
    onConfirm: () => void | Promise<void>
  }>({
    isOpen: false,
    title: '',
    description: '',
    variant: 'default',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    onConfirm: () => {},
  })

  const confirm = useCallback(
    (options: {
      title: string
      description: string
      variant?: ConfirmDialogVariant
      confirmText?: string
      cancelText?: string
      onConfirm: () => void | Promise<void>
    }) => {
      setState({
        isOpen: true,
        title: options.title,
        description: options.description,
        variant: options.variant ?? 'default',
        confirmText: options.confirmText ?? 'Confirm',
        cancelText: options.cancelText ?? 'Cancel',
        onConfirm: options.onConfirm,
      })
    },
    []
  )

  const close = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: false }))
  }, [])

  // Convenience methods for common use cases
  const confirmDelete = useCallback(
    (options: {
      title?: string
      description: string
      onConfirm: () => void | Promise<void>
    }) => {
      confirm({
        title: options.title ?? 'Delete Item',
        description: options.description,
        variant: 'danger',
        confirmText: 'Delete',
        cancelText: 'Cancel',
        onConfirm: options.onConfirm,
      })
    },
    [confirm]
  )

  return {
    isOpen: state.isOpen,
    title: state.title,
    description: state.description,
    variant: state.variant,
    confirmText: state.confirmText,
    cancelText: state.cancelText,
    onConfirm: state.onConfirm,
    onClose: close,
    confirm,
    confirmDelete,
  }
}

export default ConfirmDialog
