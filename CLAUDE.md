# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **tk-multi-breakdown2**, a Shotgun Pipeline Toolkit (ShotGrid) application for managing scene breakdowns and referenced published files. It's part of the Flow Production Tracking ecosystem and provides tools to analyze, update, and manage file references within DCC applications.

## Architecture

### Core Components

- **Application Entry Point**: `app.py` - Main SGTK application class (`SceneBreakdown2`)
- **Core Module**: `python/tk_multi_breakdown2/` - Main application logic
- **API Layer**: `python/tk_multi_breakdown2/api/` - Core business logic
  - `manager.py` - `BreakdownManager` class for scene operations
  - `item.py` - `FileItem` class representing file references
- **UI Layer**: `python/tk_multi_breakdown2/dialog.py` - Main Qt dialog interface
- **Hooks**: `hooks/` - Engine-specific scene operations and configuration

### Key Architecture Patterns

- **Hook-based extensibility**: Engine-specific operations are implemented via hooks (Maya, Nuke, Houdini, etc.)
- **Qt-based UI**: Uses ShotGrid's `tk-framework-qtwidgets` for consistent UI components
- **Model-View pattern**: Separate models for file items (`file_item_model.py`) and history (`file_history_model.py`)
- **Background task management**: Uses `tk-framework-shotgunutils` for async operations
- **SGTK framework integration**: Built on Shotgun Pipeline Toolkit architecture

### Data Flow

1. **Scene Scanning**: `BreakdownManager.get_scene_objects()` uses engine-specific hooks to scan scene references
2. **ShotGrid Integration**: Queries published files via `get_published_files.py` hook
3. **UI Display**: File items displayed in tree/list view with status indicators
4. **Update Operations**: Reference updates executed via engine-specific scene operation hooks

## Development Commands

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api_manager.py

# Run with coverage
pytest --cov=python/tk_multi_breakdown2 tests/
```

### Code Quality
```bash
# This project follows the "black" code style (see README.md badge)
# Format code with black if available
black python/

# The project uses Azure Pipelines for CI/CD (see azure-pipelines.yml)
```

## Configuration

### App Settings (info.yml)
- `panel_mode`: Launch as panel vs dialog window
- `hook_scene_operations`: Engine-specific scene scanning logic
- `hook_get_published_files`: ShotGrid published file retrieval
- `published_file_filters`: Filters for querying published files
- `group_by_fields`: Fields available for grouping file items

### Engine Support
Supports multiple DCC engines with dedicated scene operation hooks:
- Maya (`tk-maya_scene_operations.py`)
- Nuke (`tk-nuke_scene_operations.py`)  
- Houdini (`tk-houdini_scene_operations.py`)
- VRED (`tk-vred_scene_operations.py`)
- Mari (`tk-mari_scene_operations.py`)
- Alias (`tk-alias_scene_operations.py`)

## Key Dependencies

- **SGTK Core**: `v0.20.6+`
- **ShotGrid**: `v8.20.0+`
- **Frameworks**:
  - `tk-framework-shotgunutils` (v5.8.2+) - ShotGrid utilities and background tasks
  - `tk-framework-qtwidgets` (v2.12.0+) - Qt UI components

## File Structure Context

- `python/tk_multi_breakdown2/constants.py` - Application constants
- `python/tk_multi_breakdown2/utils.py` - Utility functions
- `python/tk_multi_breakdown2/decorators.py` - UI decorators (e.g., wait_cursor)
- `tests/fixtures/` - Test configuration and sample files
- `docs/` - RST documentation files
- `style.qss` - Qt stylesheet for UI theming