/**
 * Atomic Components
 *
 * Basic building blocks: buttons, inputs, labels, icons, etc.
 * These are the smallest components that cannot be broken down further.
 */

// Existing components
export { ProtectedRoute } from './ProtectedRoute'

// New atomic components
export { Button } from './Button'
export type { ButtonProps } from './Button'

export { Input } from './Input'
export type { InputProps } from './Input'

export { Badge, TicketStatusBadge, AssetStatusBadge, ticketStatusToBadge, assetStatusToBadge } from './Badge'
export type { BadgeProps, TicketStatus, AssetStatus } from './Badge'

export { Spinner } from './Spinner'
export type { SpinnerProps } from './Spinner'

export { Avatar, AvatarGroup } from './Avatar'
export type { AvatarProps, AvatarGroupProps } from './Avatar'

export { Icon, IconButton, iconSizes } from './Icon'
export type { IconProps, IconButtonProps } from './Icon'
