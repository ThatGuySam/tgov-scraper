# Jupyter Notebook Guidelines

## Automatic Output Stripping

This repository is configured with a pre-commit hook that automatically strips output cells from Jupyter notebooks before they are committed to Git. This helps keep the repository size manageable by avoiding the storage of large outputs such as images, graphs, and videos in the Git history.

### How It Works

1. The `nbstripout` pre-commit hook is configured to run automatically before each commit.
2. It removes all output cells, execution counts, and metadata from notebooks.
3. Your notebook file will be stripped only in the Git repository - your local file will keep its outputs.

### Setup for New Contributors

If you're newly cloning this repository, you need to set up the pre-commit hooks:

```bash
# Install poetry dependencies including pre-commit tools
poetry install

# Install the pre-commit hooks
poetry run pre-commit install
```

### Testing the Setup

To verify that the pre-commit hooks are working correctly, you can run:

```bash
poetry run pre-commit run --all-files
```

### Manual Stripping

If you need to manually strip outputs from a notebook, run:

```bash
poetry run nbstripout notebooks/your_notebook.ipynb
```

## Best Practices

1. **Keep Large Data Outside Git**: Store large datasets separately (e.g., data/ directory which is gitignored).
2. **Avoid Embedding Large Files**: Don't embed videos, large images, or other binary data directly in notebooks.
3. **Document Data Sources**: Always include information on how to obtain data needed for your notebooks.
4. **Separate Code and Content**: Use markdown cells to document your analysis thoroughly.

## Troubleshooting

If you encounter issues with the pre-commit hooks, ensure:
- You have run `poetry install` to install all dependencies
- You have run `poetry run pre-commit install` to set up the hooks
- You are committing from within the Poetry environment or using `poetry run git commit`
