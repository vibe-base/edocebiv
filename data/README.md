# Project Data Directory

This directory contains data for each project. Each project has its own subdirectory named `project_<id>`.

These directories are mounted as volumes to the Docker containers for each project, allowing persistent storage of data between container restarts.

## Directory Structure

```
data/
├── project_1/
│   └── (project 1 files)
├── project_2/
│   └── (project 2 files)
└── ...
```

## Mounting

When a container is created for a project, the project's data directory is mounted to `/app/data` inside the container.
