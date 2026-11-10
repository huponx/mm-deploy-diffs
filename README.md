# mm-deploy-diffs

GitHub Pages site with the rendered manifest diffs of the `mm-deploy` pull requests. It is written by the
`argocd-manifest-diff` action (do not edit it by hand):

```
<env>/<app>/<old>...<new>.html     diff between two versions of an Application
<env>/<app>/new-<version>.html     an Application that was added
index.html                         list of all pages, newest first
```

The pages are public and not redacted (rendered ConfigMap values, hostnames, Secret names).

## Clean-up

[`clean.yml`](.github/workflows/clean.yml) runs every Monday at 03:00 UTC (and on demand) and:

1. deletes the pages older than `KEEP_DAYS` days (age = date of the last commit that touched the page),
2. regenerates `index.html`,
3. squashes the history into one commit and force-pushes it, so the deleted pages also leave the git history.

Set the retention (default 90 days) as a repository variable of **this** repository:

```bash
gh variable set KEEP_DAYS --body 90 --repo huponx/mm-deploy-diffs
```

Run it by hand with `gh workflow run clean.yml --repo huponx/mm-deploy-diffs -f days=30 -f dry-run=true`
(`dry-run` only lists what would be deleted, the list is in the job summary).

Notes:

- The squash needs the default branch to allow force pushes (no branch protection on `main`).
- Because the history is squashed, [`.diffs-ages.json`](.diffs-ages.json) keeps the real age of every page that
  survives; do not delete it.
- A publish that runs at the same moment as the squash retries by itself; nothing is lost.
