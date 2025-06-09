# Version Management System

This document describes the version management system implemented for the Inventory Management System.

## Overview

The version management system provides:
- Semantic versioning (MAJOR.MINOR.PATCH.BUILD)
- Automatic build timestamp tracking
- Git integration for commit and branch information
- Web interface for viewing version information
- Changelog tracking

## Version Format

The version follows this format: `MAJOR.MINOR.PATCH.BUILD`

- **MAJOR**: Breaking changes or major feature releases (e.g., 1.0.0)
- **MINOR**: New features with backward compatibility (e.g., 0.6.0)
- **PATCH**: Bug fixes and small improvements (e.g., 0.5.1)
- **BUILD**: Automatic increment for each deployment (e.g., 0.5.0.2)

## Current Version Structure

Starting version: **0.5.0.1** (Luna)

## Files

### Core Files
- `version.py` - Main version management module
- `increment_version.py` - Script to increment version numbers
- `templates/admin/system_config.html` - System configuration page with version info
- `templates/admin/changelog.html` - Changelog page
- `VERSION_MANAGEMENT.md` - This documentation

### Key Functions
- `get_version_string()` - Returns formatted version (e.g., "v0.5.0.2")
- `get_full_version_info()` - Returns complete version metadata
- `increment_build()` - Programmatically increment build number

## Usage

### Viewing Version Information

1. **System Configuration Page**
   - Navigate to Admin → System Configuration
   - Version information is displayed in a prominent section
   - Includes build date, time, and git information
   - Direct link to changelog

2. **Changelog Page**
   - Navigate to Admin → Changelog
   - Or click "Changelog" button on System Configuration
   - Shows current version and detailed release notes

### Incrementing Versions

Use the `increment_version.py` script:

```bash
# Increment build number (most common)
python3 increment_version.py build

# Increment patch version
python3 increment_version.py patch

# Increment minor version
python3 increment_version.py minor

# Increment major version
python3 increment_version.py major
```

### Examples

```bash
# Current: 0.5.0.2
python3 increment_version.py build  # → 0.5.0.3
python3 increment_version.py patch  # → 0.5.1.1
python3 increment_version.py minor  # → 0.6.0.1
python3 increment_version.py major  # → 1.0.0.1
```

## Deployment Workflow

1. **Make changes to the codebase**
2. **Increment version** (based on change type):
   ```bash
   python3 increment_version.py [build|patch|minor|major]
   ```
3. **Update changelog** if needed (edit `templates/admin/changelog.html`)
4. **Commit changes**:
   ```bash
   git add version.py
   git commit -m "Increment version to $(python3 -c 'from version import VERSION_FULL; print(VERSION_FULL)')"
   ```
5. **Deploy application**

## Web Interface Features

### System Configuration Page
- **Version Card**: Prominent display of current version
- **Build Information**: Date, time, and git details
- **Changelog Link**: Direct access to release notes

### Changelog Page
- **Current Version Badge**: Highlights active version
- **Release History**: Detailed notes for each version
- **Roadmap Section**: Planned future releases
- **Development Notes**: Version management instructions

## Git Integration

The system automatically detects:
- Current git branch
- Latest commit hash
- Handles cases where git is not available

## Version Metadata

The `VERSION_INFO` dictionary contains:
```python
{
    'version': '0.5.0',           # MAJOR.MINOR.PATCH
    'version_full': '0.5.0.2',    # Full version with build
    'major': 0,                   # Major version number
    'minor': 5,                   # Minor version number
    'patch': 0,                   # Patch version number
    'build': 2,                   # Build number
    'build_date': '2025-06-09',   # Build date
    'build_time': '11:02:30',     # Build time
    'git_commit': 'abc123',       # Git commit hash
    'git_branch': 'main',         # Git branch
    'name': 'Inventory Management System',
    'codename': 'Luna'            # Release codename
}
```

## Release Codenames

- **0.5.x**: Luna
- **0.6.x**: (TBD - Analytics Release)
- **0.7.x**: (TBD - API Release)
- **1.0.x**: (TBD - Stable Release)

## Automatic Build Increment

For continuous integration/deployment systems, you can programmatically increment the build number:

```python
from version import increment_build
new_version = increment_build()
print(f"New version: {new_version}")
```

## Notes

- Build timestamps are automatically updated when using `increment_version.py`
- Git information is gathered at runtime (safe if git is not available)
- Version information is displayed to all logged-in users
- Only super admins can access the full system configuration page
- Changelog is accessible to all logged-in users

## Future Enhancements

- API endpoint for version information
- Automated version increment on deployment
- Integration with CI/CD pipelines
- Release notes automation
- Version comparison tools 