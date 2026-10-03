# Cleanup task: one file for the home page

Give this whole file to the coding tool that will do the work.

## Goal

The public home page ("/") is reachable through two files in `frontend/`:

- `src/app/(public)/page.tsx`: the real landing page (it also exports
  `metadata`);
- `src/app/page.tsx`: one line, `export { default } from "./(public)/page";`.

A route group such as `(public)` does not add a path segment, so both files
claim "/". The build passes today, but the setup is confusing and fragile.
Leave exactly one file serving "/", with no visible change for visitors.

## Find out first, then change

1. With the current code, record what "/" serves: the page title and meta
   description in the HTML `<head>`, the HTTP status, and the main heading.
   Note which of the two files Next.js is actually using, and whether the
   `metadata` exported by `(public)/page.tsx` reaches the page today.
2. Remove the duplication. The expected fix is to delete `src/app/page.tsx`
   and keep `src/app/(public)/page.tsx`. If your findings in step 1 show that
   this would change the title, description or content, stop and report
   instead of forcing it.
3. Record the same facts again. They must be the same as in step 1, except
   for anything that was wrong before because of the duplication (say so
   explicitly if that is the case).

`src/app/(public)/contact/page.tsx` must keep working at "/contact".

## Rules

- Do not change the landing page's content, styling or components.
- Do not touch anything under `src/app/(app)` or `src/app/(auth)`.
- Do not change `next.config.js`.
- No new dependencies.

## Checks (the frontend runs in Docker as `frontend-dev`, mounted from `frontend/`)

Type check:

```bash
docker exec frontend-dev sh -c "cd /app; npx tsc --noEmit -p ."
```

Tests (expected: 15 passed):

```bash
docker exec frontend-dev sh -c "cd /app; npx vitest run"
```

Production build, in a separate folder so it does not disturb the running dev
server:

```bash
docker exec -e NEXT_DIST_DIR=.next-check frontend-dev sh -c "cd /app; npx next build; rm -rf .next-check"
```

The build rewrites two tracked files. Put them back afterwards, or the next
build can fail on "/":

```bash
git checkout frontend/tsconfig.json frontend/next-env.d.ts
```

Then confirm in the running dev server (`http://localhost:3000`) that "/",
"/contact" and "/login" each answer with status 200.

## How to work

- Create a new branch from `feature/cs-automation-live-desk` called
  `cleanup/home-page`. Do not commit to the feature branch, do not push, do not
  merge.
- One commit.

## What to report back

- Which file was serving "/" before, and what you removed.
- Title, description, status and main heading before and after.
- The results of the three checks and the three URL checks.
