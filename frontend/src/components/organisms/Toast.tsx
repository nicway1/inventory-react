/**
 * Toast Component and useToast Hook
 *
 * A toast notification system with support for multiple toast types,
 * stacking, auto-dismiss, and action buttons.
 */

import React, { useEffect, useCallback } from 'react'
import { Transition } from '@headlessui/react'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useUIStore } from '@/store/ui.store'

// Toast types
export type ToastType = 'success' | 'error' | 'warning' | 'info'

// Toast position options
export type ToastPosition =
  | 'top-left'
  | 'top-center'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-center'
  | 'bottom-right'

// Extended Toast interface with action support
export interface ToastData {
  id: string
  type: ToastType
  message: string
  title?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

// Toast item props
interface ToastItemProps {
  toast: ToastData
  onDismiss: (id: string) => void
}

// Icon and styling configuration per toast type - Salesforce Lightning
const toastConfig: Record<
  ToastType,
  {
    icon: React.ElementType
    bgClass: string
    iconClass: string
    progressClass: string
  }
> = {
  success: {
    icon: CheckCircleIcon,
    bgClass: 'bg-white border-l-4 border-l-[#2E844A] shadow-[0_2px_8px_rgba(0,0,0,0.16)]',
    iconClass: 'text-[#2E844A]',
    progressClass: 'bg-[#2E844A]',
  },
  error: {
    icon: ExclamationCircleIcon,
    bgClass: 'bg-white border-l-4 border-l-[#C23934] shadow-[0_2px_8px_rgba(0,0,0,0.16)]',
    iconClass: 'text-[#C23934]',
    progressClass: 'bg-[#C23934]',
  },
  warning: {
    icon: ExclamationTriangleIcon,
    bgClass: 'bg-white border-l-4 border-l-[#FE9339] shadow-[0_2px_8px_rgba(0,0,0,0.16)]',
    iconClass: 'text-[#FE9339]',
    progressClass: 'bg-[#FE9339]',
  },
  info: {
    icon: InformationCircleIcon,
    bgClass: 'bg-white border-l-4 border-l-[#0176D3] shadow-[0_2px_8px_rgba(0,0,0,0.16)]',
    iconClass: 'text-[#0176D3]',
    progressClass: 'bg-[#0176D3]',
  },
}

// Position classes mapping
const positionClasses: Record<ToastPosition, string> = {
  'top-left': 'top-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'top-right': 'top-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
  'bottom-right': 'bottom-4 right-4',
}

// Default duration for auto-dismiss (in ms)
const DEFAULT_DURATION = 5000

// Individual Toast Item Component
function ToastItem({ toast, onDismiss }: ToastItemProps) {
  const { icon: Icon, bgClass, iconClass, progressClass } = toastConfig[toast.type]
  const duration = toast.duration ?? DEFAULT_DURATION

  // Auto-dismiss effect
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onDismiss(toast.id)
      }, duration)
      return () => clearTimeout(timer)
    }
  }, [toast.id, duration, onDismiss])

  return (
    <Transition
      appear
      show
      enter="transform transition duration-300 ease-out"
      enterFrom="translate-x-full opacity-0"
      enterTo="translate-x-0 opacity-100"
      leave="transform transition duration-200 ease-in"
      leaveFrom="translate-x-0 opacity-100"
      leaveTo="translate-x-full opacity-0"
    >
      <div
        className={cn(
          'relative w-80 rounded overflow-hidden',
          bgClass
        )}
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-start gap-3 p-4">
          <Icon className={cn('w-5 h-5 flex-shrink-0 mt-0.5', iconClass)} />
          <div className="flex-1 min-w-0">
            {toast.title && (
              <p className="text-sm font-semibold text-gray-900">{toast.title}</p>
            )}
            <p className={cn('text-sm text-gray-700', toast.title && 'mt-1')}>
              {toast.message}
            </p>
            {toast.action && (
              <button
                type="button"
                onClick={() => {
                  toast.action?.onClick()
                  onDismiss(toast.id)
                }}
                className={cn(
                  'mt-2 text-sm font-medium',
                  iconClass,
                  'hover:underline focus:outline-none'
                )}
              >
                {toast.action.label}
              </button>
            )}
          </div>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            className="flex-shrink-0 p-1 text-[#706E6B] rounded hover:text-gray-700 hover:bg-[#F4F6F9] focus:outline-none focus:ring-2 focus:ring-[#0176D3]"
          >
            <span className="sr-only">Dismiss</span>
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
        {/* Progress bar for auto-dismiss */}
        {duration > 0 && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-100">
            <div
              className={cn('h-full', progressClass)}
              style={{
                animation: `shrink ${duration}ms linear forwards`,
              }}
            />
          </div>
        )}
      </div>
    </Transition>
  )
}

// Toast Container Props
export interface ToastContainerProps {
  position?: ToastPosition
  className?: string
}

// Toast Container Component
export function ToastContainer({
  position = 'top-right',
  className,
}: ToastContainerProps) {
  const { toasts, removeToast } = useUIStore()

  const handleDismiss = useCallback(
    (id: string) => {
      removeToast(id)
    },
    [removeToast]
  )

  if (toasts.length === 0) return null

  return (
    <>
      {/* Inject keyframes for progress animation */}
      <style>
        {`
          @keyframes shrink {
            from { width: 100%; }
            to { width: 0%; }
          }
        `}
      </style>
      <div
        aria-live="polite"
        aria-atomic="true"
        className={cn(
          'fixed z-50 flex flex-col gap-2 pointer-events-none',
          positionClasses[position],
          className
        )}
      >
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem
              toast={toast as ToastData}
              onDismiss={handleDismiss}
            />
          </div>
        ))}
      </div>
    </>
  )
}

// useToast Hook
export function useToast() {
  const { addToast, removeToast, clearToasts } = useUIStore()

  const toast = useCallback(
    (options: Omit<ToastData, 'id'>) => {
      addToast(options)
    },
    [addToast]
  )

  const success = useCallback(
    (message: string, options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>) => {
      addToast({ type: 'success', message, ...options })
    },
    [addToast]
  )

  const error = useCallback(
    (message: string, options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>) => {
      addToast({ type: 'error', message, ...options })
    },
    [addToast]
  )

  const warning = useCallback(
    (message: string, options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>) => {
      addToast({ type: 'warning', message, ...options })
    },
    [addToast]
  )

  const info = useCallback(
    (message: string, options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>) => {
      addToast({ type: 'info', message, ...options })
    },
    [addToast]
  )

  const dismiss = useCallback(
    (id: string) => {
      removeToast(id)
    },
    [removeToast]
  )

  const dismissAll = useCallback(() => {
    clearToasts()
  }, [clearToasts])

  return {
    toast,
    success,
    error,
    warning,
    info,
    dismiss,
    dismissAll,
  }
}

export default ToastContainer
