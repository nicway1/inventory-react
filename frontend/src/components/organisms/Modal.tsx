/**
 * Modal Component
 *
 * A fully accessible modal dialog using Headless UI.
 * Supports multiple sizes, animations, and focus trapping.
 */

import React, { Fragment } from 'react'
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Transition,
  TransitionChild,
} from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'

export interface ModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Callback when the modal should close */
  onClose: () => void
  /** Modal title */
  title: string
  /** Modal size variant */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  /** Modal content */
  children: React.ReactNode
  /** Footer content (buttons, etc.) */
  footer?: React.ReactNode
  /** Whether to show the close button */
  showCloseButton?: boolean
  /** Whether clicking the backdrop closes the modal */
  closeOnBackdropClick?: boolean
  /** Additional class name for the modal panel */
  className?: string
  /** Additional class name for the content area */
  contentClassName?: string
}

// Size classes mapping
const sizeClasses: Record<NonNullable<ModalProps['size']>, string> = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
  xl: 'sm:max-w-xl',
  full: 'sm:max-w-4xl lg:max-w-6xl',
}

export function Modal({
  isOpen,
  onClose,
  title,
  size = 'md',
  children,
  footer,
  showCloseButton = true,
  closeOnBackdropClick = true,
  className,
  contentClassName,
}: ModalProps) {
  const handleBackdropClick = () => {
    if (closeOnBackdropClick) {
      onClose()
    }
  }

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-50"
        onClose={handleBackdropClick}
      >
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

        {/* Modal container */}
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex items-center justify-center min-h-full p-4 text-center sm:p-0">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel
                className={cn(
                  'relative w-full transform overflow-hidden rounded bg-white text-left shadow-xl transition-all',
                  sizeClasses[size],
                  className
                )}
              >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 bg-[#F3F3F3] border-b border-[#DDDBDA]">
                  <DialogTitle
                    as="h3"
                    className="text-lg font-semibold leading-6 text-gray-900"
                  >
                    {title}
                  </DialogTitle>
                  {showCloseButton && (
                    <button
                      type="button"
                      onClick={onClose}
                      className="p-1 text-[#706E6B] transition-colors rounded hover:text-gray-700 hover:bg-[#DDDBDA] focus:outline-none focus:ring-2 focus:ring-[#0176D3]"
                    >
                      <span className="sr-only">Close</span>
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {/* Content */}
                <div
                  className={cn(
                    'px-6 py-4 overflow-y-auto max-h-[calc(100vh-16rem)]',
                    contentClassName
                  )}
                >
                  {children}
                </div>

                {/* Footer */}
                {footer && (
                  <div className="flex items-center justify-end gap-3 px-6 py-4 bg-[#F3F3F3] border-t border-[#DDDBDA]">
                    {footer}
                  </div>
                )}
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

export default Modal
