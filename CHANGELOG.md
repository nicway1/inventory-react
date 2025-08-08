# Changelog

All notable changes to the TrueLog Inventory Management System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.3.1] - 2025-08-08

### 🚀 New Features

#### Group @Mention System
- **Complete Group Management Interface** - Accessible via System Configuration → Group Management
- **Create and Manage Groups** - Full CRUD operations for group creation, editing, and member management
- **Group @Mentions** - Users can now @mention group names (e.g., @developers, @support-team) to notify all group members
- **Smart Mention Detection** - Automatically differentiates between user mentions and group mentions
- **Group Member Management** - Add/remove users from groups with real-time interface updates
- **Group Status Control** - Activate/deactivate groups as needed

#### Enhanced Notification System
- **Group Mention Notifications** - All group members receive notifications when their group is mentioned
- **Customized Email Alerts** - Email notifications clearly indicate group mentions vs. direct mentions
- **Database Notifications** - Persistent notifications stored in database with group mention tracking
- **Activity Feed Integration** - Group mentions appear in user activity feeds
- **Self-Exclusion Logic** - Users don't receive notifications when they mention groups they belong to

#### Admin Features
- **Comprehensive Group Interface** - Modern, Ajax-powered group management with real-time updates
- **Group Validation** - Proper naming conventions enforced (lowercase, hyphens allowed)
- **Member Search & Selection** - Easy user selection for group membership
- **Group Analytics** - Member count tracking and membership history

### 🔧 Technical Improvements

#### Database Schema
- **New Groups Table** - Stores group information with proper relationships
- **Group Memberships Table** - Manages user-group relationships with tracking
- **Enhanced User Model** - Added group-related properties and helper methods
- **Extended Comment Model** - Enhanced mention detection capabilities

#### API Enhancements
- **Group Management Endpoints** - Complete REST API for group operations
- **Enhanced Comment Processing** - Improved @mention parsing and notification dispatch
- **Notification Service Updates** - Group mention notification creation and management
- **Email Service Integration** - Group mention email template support

#### Code Quality
- **Comprehensive Testing** - Full test suite for group functionality
- **Debug Tools** - Diagnostic scripts for troubleshooting group issues
- **Documentation** - Complete implementation documentation
- **Migration Scripts** - Safe database migration for existing installations

### 🐛 Bug Fixes

#### Comment System
- **Fixed Comment Constructor** - Resolved queue change comment creation issues
- **Improved Error Handling** - Better error messages for group membership operations
- **Type Conversion** - Proper integer handling for user and group IDs
- **Data Validation** - Enhanced validation for group names and member operations

### 💫 User Experience

#### Interface Improvements
- **Intuitive Group Management** - Clean, modern interface for all group operations
- **Real-time Updates** - Ajax-powered interface with immediate feedback
- **Responsive Design** - Mobile-friendly group management interface
- **Clear Error Messages** - Detailed feedback for group operation failures

#### Notification Experience
- **Clear Group Context** - Users understand why they received notifications
- **Professional Email Design** - Consistent styling with existing email templates
- **Multiple Notification Channels** - Database, email, and activity feed notifications

### 🔒 Security & Permissions
- **Admin-Only Group Management** - Only administrators can create and manage groups
- **Proper Access Control** - Group operations respect existing permission system
- **Input Validation** - Comprehensive validation for all group-related inputs
- **Safe Member Operations** - Protected add/remove operations with proper error handling

### 📚 Migration & Deployment
- **Database Migration Script** - `add_groups_tables.py` for safe schema updates
- **Backward Compatibility** - Fully compatible with existing @mention functionality
- **Zero-Downtime Migration** - Safe deployment process for production environments

## [0.6.1] - 2025-06-22

### 🎨 User Interface Improvements

#### System Management Dashboard Redesign
- **Redesigned System Management card** with modern, professional styling
- **Simplified navigation** with only 7 essential functions:
  - Manage Users
  - Manage Companies  
  - Create New User
  - Unified Permissions Management
  - View System History
  - System Configuration
- **Beautiful gradient backgrounds** for each button with subtle color coding
- **Uniform button sizing** with consistent 3-column grid layout
- **Enhanced visual hierarchy** with improved spacing and typography

#### Unified Permissions Management
- **New unified permissions page** combining user and queue permissions
- **Tab-based interface** for seamless switching between permission types
- **Modern purple-themed design** with professional card layouts
- **Quick action buttons** for common permission tasks
- **Streamlined navigation** reducing complexity from 2 buttons to 1

### 🔧 Technical Improvements

#### Route Management
- **New unified permissions route** (`/admin/permissions/unified`)
- **Proper database session management** following existing patterns
- **Fixed BuildError issues** with correct URL endpoint references
- **Consistent error handling** across all admin routes

#### UI/UX Enhancements
- **Responsive design improvements** for better mobile experience
- **Smooth hover effects** and transitions for interactive elements
- **Professional color scheme** maintaining business-appropriate styling
- **Improved accessibility** with better contrast and button sizing

### 🐛 Bug Fixes

#### Dashboard Loading Issues
- **Fixed port conflict errors** when starting the application
- **Corrected route name references** from `main.home` to `main.index`
- **Resolved BuildError** in unified permissions template
- **Improved error handling** for database session management

#### Visual Consistency
- **Fixed inconsistent button sizes** in System Management card
- **Standardized color palette** across admin interface
- **Improved layout alignment** and spacing consistency
- **Enhanced text readability** with better typography choices

### 📱 User Experience

#### Navigation Improvements
- **Simplified admin navigation** with fewer, more intuitive options
- **Clear visual feedback** for interactive elements
- **Consistent design language** across all admin pages
- **Better organization** of system management functions

#### Performance Optimizations
- **Faster page loading** with optimized CSS and JavaScript
- **Reduced cognitive load** with cleaner, more focused interfaces
- **Improved responsiveness** across different screen sizes
- **Better accessibility** compliance with modern web standards

---

## [0.6.0] - 2025-06-11

### 🎉 Major Features Added

#### Microsoft 365 OAuth2 Email Integration
- **Complete Microsoft 365 OAuth2 integration** using Azure App Registration
- **Corporate email sending** from `support@truelog.com.sg` 
- **Smart fallback system**: Microsoft Graph API primary, Gmail SMTP backup
- **Beautiful HTML email templates** with professional branding
- **Secure authentication** using client credentials flow

#### Advanced Billing Generator System
- **Monthly billing report generation** with Excel export
- **Multi-country support** with separate sheets per country
- **Flexible fee calculation** based on ticket categories:
  - Checkout tickets: $500 order fee + $80 receiving
  - Return tickets: $240 return fee + $80 receiving  
  - Intake tickets: $1100 intake fee + $80 receiving
  - Storage fee: $10 per ticket (monthly)
- **Interactive filters** by year, month, country, and company
- **AJAX ticket loading** for smooth user experience
- **Summary and detailed reporting** with professional formatting

#### Enhanced @Mention System
- **Salesforce-style email notifications** for @mentions in ticket comments
- **Real-time mention detection** with autocomplete suggestions
- **Beautiful HTML email templates** with ticket context
- **Microsoft 365 integration** for professional delivery
- **Activity tracking** for mentioned users

### 🔧 Technical Improvements

#### Email Infrastructure
- **Unified email sending architecture** in `utils/email_sender.py`
- **Microsoft Graph API client** in `utils/microsoft_email.py`
- **Environment variable configuration** for easy deployment
- **Error handling and logging** for robust email delivery

#### User Interface Enhancements
- **Modern billing generator interface** with real-time updates
- **Excel export functionality** with multiple sheets
- **Improved admin panel** with new configuration options
- **Enhanced system configuration** display

#### Backend Architecture
- **Route organization** for billing and admin functions
- **Database query optimization** for billing calculations
- **Excel generation** using pandas and openpyxl
- **CSRF protection** for all forms

### 📧 Email System Details

#### Welcome Emails
- **Professional onboarding emails** for new users
- **Account credentials delivery** with security instructions
- **Branded HTML templates** with company styling

#### Mention Notifications
- **@username detection** in ticket comments
- **Instant email delivery** via Microsoft Graph API
- **Rich HTML formatting** with ticket context
- **Direct links** back to tickets

#### Test Email System
- **Admin panel email testing** with Microsoft 365 verification
- **Connection status monitoring** and troubleshooting
- **Real-time configuration validation**

### 🏢 Microsoft 365 Configuration

#### Azure App Registration
- **Application permissions**: `Mail.Send`, `User.Read.All`
- **OAuth2 client credentials** flow implementation
- **Secure token management** with automatic refresh
- **Corporate domain authentication**

#### Environment Variables
```env
MS_CLIENT_ID=your-azure-client-id
MS_CLIENT_SECRET=your-azure-client-secret  
MS_TENANT_ID=your-azure-tenant-id
MS_FROM_EMAIL=support@truelog.com.sg
USE_OAUTH2_EMAIL=true
```

### 💰 Billing System Features

#### Report Generation
- **Flexible date range selection** (year/month)
- **Multi-company support** with separate calculations
- **Country-based organization** for international operations
- **Real-time ticket filtering** with AJAX

#### Excel Export
- **Summary sheet** with totals by country
- **Detailed sheets** per country with line items
- **Professional formatting** with headers and styling
- **Automatic file download** with descriptive naming

#### Fee Structure
- **Configurable fee types** based on ticket categories
- **Monthly storage calculations** for ongoing costs
- **Order processing fees** for checkout operations
- **Return handling fees** for return tickets

### 🔄 Migration and Deployment

#### Database Updates
- **Preserved existing data** during email system migration
- **Backward compatibility** with existing email functions
- **Graceful degradation** to SMTP if OAuth2 fails

#### Configuration Management
- **Environment-based configuration** for different deployments
- **Secure credential storage** in `.env` files
- **Runtime configuration** validation and testing

### 🧪 Testing and Quality

#### Comprehensive Testing
- **Email delivery verification** scripts
- **Microsoft Graph API** connection testing
- **Billing calculation** accuracy validation
- **Cross-browser compatibility** testing

#### Debugging Tools
- **Detailed logging** for email operations
- **Test email functionality** in admin panel
- **System status monitoring** for Microsoft 365 integration

### 📚 Documentation

#### Setup Guides
- **Microsoft 365 configuration** step-by-step instructions
- **Azure App Registration** detailed walkthrough
- **Environment variable** configuration guide
- **Troubleshooting** common issues and solutions

### 🚀 Performance Improvements

#### Email Delivery
- **Microsoft Graph API** for faster email delivery
- **Connection pooling** and token caching
- **Async processing** for mention notifications
- **Fallback mechanisms** for reliability

#### Billing Processing
- **Optimized database queries** for large datasets
- **Efficient Excel generation** with streaming
- **Client-side filtering** for better responsiveness
- **Caching** for repeated calculations

### 🔐 Security Enhancements

#### OAuth2 Implementation
- **Secure token storage** and refresh handling
- **Client credentials** flow for server-to-server auth
- **Encrypted communication** with Microsoft Graph
- **Access token** expiration management

#### Data Protection
- **CSRF protection** on all forms
- **Input validation** for billing parameters
- **Secure email** template rendering
- **Environment variable** protection

### 🎨 User Experience

#### Modern Interface
- **Responsive design** for billing generator
- **Real-time updates** without page refreshes
- **Progress indicators** for long operations
- **Intuitive navigation** and form layouts

#### Professional Emails
- **Salesforce-inspired** email templates
- **Corporate branding** with TrueLog styling
- **Mobile-friendly** HTML email design
- **Clear call-to-action** buttons

---

## Previous Versions

### [0.5.1] - 2025-06-09
- Bug fixes and stability improvements
- Performance optimizations
- Enhanced user interface

### [0.5.0] - 2025-06-08
- Core inventory management features
- Basic email functionality
- User authentication system
- Ticket management

---

**Note**: This changelog documents major features and improvements. For detailed technical changes, see the git commit history. 