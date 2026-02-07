/**
 * Profile Page
 *
 * User profile management page with:
 * - User info display (username, email, role, company)
 * - Edit profile form
 * - Change password form
 * - Profile picture upload
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  UserCircleIcon,
  EnvelopeIcon,
  BuildingOfficeIcon,
  ShieldCheckIcon,
  CameraIcon,
  PencilIcon,
  KeyIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useAuthStore } from '@/store/auth.store'
import { useUIStore } from '@/store/ui.store'
import { profileService } from '@/services/preferences.service'
import { PageLayout } from '@/components/templates/PageLayout'
import { Card, CardHeader, CardBody } from '@/components/molecules/Card'
import { Input } from '@/components/atoms/Input'
import { Button } from '@/components/atoms/Button'
import { Avatar } from '@/components/atoms/Avatar'

/**
 * Profile form validation schema
 */
const profileSchema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  email: z.string().email('Invalid email address'),
  username: z.string().min(3, 'Username must be at least 3 characters'),
})

type ProfileFormData = z.infer<typeof profileSchema>

/**
 * Password change validation schema
 */
const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
      .regex(/[0-9]/, 'Password must contain at least one number'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  })

type PasswordFormData = z.infer<typeof passwordSchema>

/**
 * User role badge component
 */
function RoleBadge({ role }: { role: string }) {
  const roleColors: Record<string, string> = {
    SUPER_ADMIN: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    DEVELOPER: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    SUPERVISOR: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    COUNTRY_ADMIN: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    TECHNICIAN: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
    CLIENT: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
  }

  const displayRole = role.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        roleColors[role] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
      )}
    >
      {displayRole}
    </span>
  )
}

/**
 * Alert component for success/error messages
 */
function Alert({
  type,
  message,
  onClose,
}: {
  type: 'success' | 'error'
  message: string
  onClose?: () => void
}) {
  const colors = {
    success: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800',
    error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800',
  }
  const textColors = {
    success: 'text-green-800 dark:text-green-200',
    error: 'text-red-800 dark:text-red-200',
  }
  const icons = {
    success: CheckCircleIcon,
    error: ExclamationCircleIcon,
  }

  const Icon = icons[type]

  return (
    <div className={cn('p-4 rounded-lg border flex items-start gap-3', colors[type])}>
      <Icon className={cn('w-5 h-5 flex-shrink-0 mt-0.5', textColors[type])} />
      <p className={cn('text-sm flex-1', textColors[type])}>{message}</p>
      {onClose && (
        <button
          onClick={onClose}
          className={cn('flex-shrink-0', textColors[type], 'hover:opacity-70')}
        >
          <XMarkIcon className="w-5 h-5" />
        </button>
      )}
    </div>
  )
}

/**
 * Profile Page component
 */
export function ProfilePage() {
  const { user, setUser } = useAuthStore()
  const { addToast } = useUIStore()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // State
  const [isEditingProfile, setIsEditingProfile] = useState(false)
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)
  const [profileAlert, setProfileAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [passwordAlert, setPasswordAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleSubmitProfile,
    formState: { errors: profileErrors, isSubmitting: isSubmittingProfile },
    reset: resetProfile,
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || '',
      email: user?.email || '',
      username: user?.username || '',
    },
  })

  // Password form
  const {
    register: registerPassword,
    handleSubmit: handleSubmitPassword,
    formState: { errors: passwordErrors, isSubmitting: isSubmittingPassword },
    reset: resetPassword,
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })

  // Reset profile form when user changes
  useEffect(() => {
    if (user) {
      resetProfile({
        full_name: user.full_name || '',
        email: user.email || '',
        username: user.username || '',
      })
    }
  }, [user, resetProfile])

  /**
   * Handle profile form submission
   */
  const onProfileSubmit = async (data: ProfileFormData) => {
    setProfileAlert(null)
    try {
      const response = await profileService.updateProfile(data)
      if (response.success) {
        setUser(response.data)
        setProfileAlert({ type: 'success', message: 'Profile updated successfully' })
        setIsEditingProfile(false)
        addToast({
          type: 'success',
          message: 'Profile updated successfully.',
        })
      } else {
        setProfileAlert({ type: 'error', message: response.message || 'Failed to update profile' })
      }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { message?: string } } }).response?.data?.message || 'Failed to update profile'
          : 'An error occurred'
      setProfileAlert({ type: 'error', message })
    }
  }

  /**
   * Handle password change submission
   */
  const onPasswordSubmit = async (data: PasswordFormData) => {
    setPasswordAlert(null)
    try {
      const response = await profileService.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
        confirm_password: data.confirm_password,
      })
      if (response.success) {
        setPasswordAlert({ type: 'success', message: 'Password changed successfully' })
        setIsChangingPassword(false)
        resetPassword()
        addToast({
          type: 'success',
          message: 'Password changed successfully.',
        })
      } else {
        setPasswordAlert({ type: 'error', message: response.message || 'Failed to change password' })
      }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { message?: string } } }).response?.data?.message || 'Failed to change password'
          : 'An error occurred'
      setPasswordAlert({ type: 'error', message })
    }
  }

  /**
   * Handle avatar upload
   */
  const handleAvatarUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      addToast({
        type: 'error',
        message: 'Invalid file type. Please select an image file.',
      })
      return
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      addToast({
        type: 'error',
        message: 'File too large. Image must be less than 5MB.',
      })
      return
    }

    setIsUploadingAvatar(true)
    try {
      const response = await profileService.uploadProfilePicture(file)
      if (response.success && user) {
        // Update user with new avatar URL
        setUser({ ...user, avatar_url: response.data.avatar_url } as typeof user)
        addToast({
          type: 'success',
          message: 'Profile picture updated successfully.',
        })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: 'Failed to upload profile picture.',
      })
    } finally {
      setIsUploadingAvatar(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }, [user, setUser, addToast])

  /**
   * Handle avatar delete
   */
  const handleAvatarDelete = useCallback(async () => {
    setIsUploadingAvatar(true)
    try {
      const response = await profileService.deleteProfilePicture()
      if (response.success && user) {
        // Remove avatar URL from user
        const { ...userWithoutAvatar } = user as typeof user & { avatar_url?: string }
        delete userWithoutAvatar.avatar_url
        setUser(userWithoutAvatar)
        addToast({
          type: 'success',
          message: 'Profile picture removed.',
        })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: 'Failed to delete profile picture.',
      })
    } finally {
      setIsUploadingAvatar(false)
    }
  }, [user, setUser, addToast])

  // Use handleAvatarDelete in a future avatar management feature
  void handleAvatarDelete

  if (!user) {
    return (
      <PageLayout title="Profile" breadcrumbs={[{ label: 'Profile' }]}>
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500 dark:text-gray-400">Please log in to view your profile.</p>
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout
      title="My Profile"
      subtitle="Manage your personal information and account settings"
      breadcrumbs={[{ label: 'Profile' }]}
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Profile Overview Card */}
        <Card>
          <CardHeader>Profile Overview</CardHeader>
          <CardBody>
            <div className="flex flex-col sm:flex-row items-center gap-6">
              {/* Avatar Section */}
              <div className="relative group">
                <Avatar
                  src={(user as typeof user & { avatar_url?: string }).avatar_url}
                  name={user.full_name || user.username}
                  size="xl"
                  className="w-24 h-24"
                />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarUpload}
                  className="hidden"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploadingAvatar}
                    className="p-2 text-white hover:text-gray-200 transition-colors"
                    title="Upload new photo"
                  >
                    <CameraIcon className="w-6 h-6" />
                  </button>
                </div>
                {isUploadingAvatar && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full">
                    <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  </div>
                )}
              </div>

              {/* User Info */}
              <div className="flex-1 text-center sm:text-left">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {user.full_name || user.username}
                </h2>
                <p className="text-gray-500 dark:text-gray-400">@{user.username}</p>
                <div className="mt-2 flex flex-wrap justify-center sm:justify-start gap-2">
                  <RoleBadge role={user.user_type} />
                  {user.company_name && (
                    <span className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
                      <BuildingOfficeIcon className="w-4 h-4" />
                      {user.company_name}
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditingProfile(!isEditingProfile)}
                  leftIcon={<PencilIcon className="w-4 h-4" />}
                >
                  Edit Profile
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Edit Profile Form */}
        {isEditingProfile && (
          <Card>
            <CardHeader>Edit Profile</CardHeader>
            <CardBody>
              {profileAlert && (
                <div className="mb-4">
                  <Alert
                    type={profileAlert.type}
                    message={profileAlert.message}
                    onClose={() => setProfileAlert(null)}
                  />
                </div>
              )}
              <form onSubmit={handleSubmitProfile(onProfileSubmit)} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Full Name"
                    placeholder="Enter your full name"
                    error={profileErrors.full_name?.message}
                    leftIcon={<UserCircleIcon className="w-5 h-5" />}
                    {...registerProfile('full_name')}
                  />
                  <Input
                    label="Username"
                    placeholder="Enter your username"
                    error={profileErrors.username?.message}
                    leftIcon={<UserCircleIcon className="w-5 h-5" />}
                    {...registerProfile('username')}
                  />
                </div>
                <Input
                  label="Email Address"
                  type="email"
                  placeholder="Enter your email"
                  error={profileErrors.email?.message}
                  leftIcon={<EnvelopeIcon className="w-5 h-5" />}
                  {...registerProfile('email')}
                />
                <div className="flex justify-end gap-3 pt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setIsEditingProfile(false)
                      setProfileAlert(null)
                      resetProfile()
                    }}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" isLoading={isSubmittingProfile}>
                    Save Changes
                  </Button>
                </div>
              </form>
            </CardBody>
          </Card>
        )}

        {/* Account Information */}
        <Card>
          <CardHeader>Account Information</CardHeader>
          <CardBody>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
                  <UserCircleIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    Username
                  </p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user.username}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-green-50 dark:bg-green-900/30">
                  <EnvelopeIcon className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    Email Address
                  </p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user.email}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-900/30">
                  <ShieldCheckIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    Role
                  </p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user.user_type.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-orange-50 dark:bg-orange-900/30">
                  <BuildingOfficeIcon className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    Company
                  </p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user.company_name || 'Not assigned'}
                  </p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Security Section */}
        <Card>
          <CardHeader
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsChangingPassword(!isChangingPassword)}
                leftIcon={<KeyIcon className="w-4 h-4" />}
              >
                {isChangingPassword ? 'Cancel' : 'Change Password'}
              </Button>
            }
          >
            Security
          </CardHeader>
          <CardBody>
            {isChangingPassword ? (
              <>
                {passwordAlert && (
                  <div className="mb-4">
                    <Alert
                      type={passwordAlert.type}
                      message={passwordAlert.message}
                      onClose={() => setPasswordAlert(null)}
                    />
                  </div>
                )}
                <form onSubmit={handleSubmitPassword(onPasswordSubmit)} className="space-y-4">
                  <Input
                    label="Current Password"
                    type="password"
                    placeholder="Enter your current password"
                    error={passwordErrors.current_password?.message}
                    leftIcon={<KeyIcon className="w-5 h-5" />}
                    {...registerPassword('current_password')}
                  />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      label="New Password"
                      type="password"
                      placeholder="Enter new password"
                      error={passwordErrors.new_password?.message}
                      leftIcon={<KeyIcon className="w-5 h-5" />}
                      {...registerPassword('new_password')}
                    />
                    <Input
                      label="Confirm New Password"
                      type="password"
                      placeholder="Confirm new password"
                      error={passwordErrors.confirm_password?.message}
                      leftIcon={<KeyIcon className="w-5 h-5" />}
                      {...registerPassword('confirm_password')}
                    />
                  </div>
                  <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
                    <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
                      Password Requirements:
                    </p>
                    <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                      <li>At least 8 characters long</li>
                      <li>At least one uppercase letter</li>
                      <li>At least one lowercase letter</li>
                      <li>At least one number</li>
                    </ul>
                  </div>
                  <div className="flex justify-end gap-3 pt-4">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        setIsChangingPassword(false)
                        setPasswordAlert(null)
                        resetPassword()
                      }}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" isLoading={isSubmittingPassword}>
                      Update Password
                    </Button>
                  </div>
                </form>
              </>
            ) : (
              <div className="text-center py-8">
                <KeyIcon className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  Keep your account secure by using a strong password.
                </p>
                <Button
                  variant="secondary"
                  onClick={() => setIsChangingPassword(true)}
                  leftIcon={<KeyIcon className="w-4 h-4" />}
                >
                  Change Password
                </Button>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </PageLayout>
  )
}

export default ProfilePage
