-- Update feature_requests status enum to include all statuses
-- This fixes the missing PENDING_APPROVAL, APPROVED, and REJECTED statuses

ALTER TABLE feature_requests
MODIFY COLUMN status ENUM(
    'REQUESTED',
    'PENDING_APPROVAL',
    'APPROVED',
    'REJECTED',
    'IN_PLANNING',
    'IN_DEVELOPMENT',
    'IN_TESTING',
    'COMPLETED',
    'CANCELLED'
) DEFAULT 'REQUESTED';
