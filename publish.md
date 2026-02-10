# How To Publish FLOWENGINE 

## Publish to PyPI                                                       
                                                                                                                                   
__NOTE__: use conda vir env
```bash
conda activate flowengine
```

WE USE poetry-core as build backend and has build + twine in dev deps.                                        

```bash
# Make sure you're on a clean commit
git add -A && git commit -m "docs: update documentation for v0.2.0"

# Build the sdist + wheel
python -m build

# Check the package looks right
twine check dist/*

# Upload to PyPI (you'll need your API token)
twine upload dist/*
```

For the API token, you have two options:
  - Interactive: twine upload will prompt for username (__token__) and password (your PyPI API token)
  - Config file: Create ~/.pypirc:
```
[pypi]
username = __token__
password = pypi-AgEIcH...your-token-here
```

To generate a PyPI API token: go to https://pypi.org/manage/account/token/

## Update ReadTheDocs

Your ReadTheDocs is already configured (.readthedocs.yaml + docs/mkdocs.yml). It builds automatically from your repo.

Just push to your remote:

```bash
  git push origin master
```

> ReadTheDocs watches your GitHub repo and automatically rebuilds when you push to the default branch. That's it — the docs at flowengine.readthedocs.io will update within a few minutes.

  If this is a first-time setup or the webhook isn't connected:
  1. Go to https://readthedocs.org/dashboard/
  2. Import your project from github.com/alexh-scrt/flowengine
  3. It will auto-detect .readthedocs.yaml and build

  ---
  TL;DR:
  - PyPI: python -m build && twine upload dist/* (with API token)
  - ReadTheDocs: Just git push — it rebuilds automatically