# `app/data/` — JSON content store

This replaced the Postgres-backed `projects`/`certificates`/`experiences`/`hackathons`
tables when the database was removed. There is no database anywhere in this
backend anymore; these four files **are** the content.

## Not durable on Render

Writes made through the admin dashboard (create/edit/delete/reorder) edit
these files on the running container's disk. **Render's filesystem does not
survive a redeploy**, and isn't guaranteed to survive a plain restart either,
depending on plan. Any edit made through the admin UI will be silently lost
the next time the service redeploys (including an automatic deploy from a
git push) unless you also commit the updated JSON file back into the repo.

Treat the admin editor as a convenience for drafting content locally or for a
same-session tweak you'll immediately commit - not as a live CMS.

## Shape

Each file is a JSON array of objects. `id` is assigned by the backend
(`app/data/store.py::_next_id`, current max `id` + 1) - never set it by hand.
The fields for each match the corresponding Pydantic schema in
`app/schemas/`:

- `projects.json` → `app.schemas.project.ProjectOut`
- `certificates.json` → `app.schemas.certificate.CertificateOut`
- `experiences.json` → `app.schemas.experience.ExperienceOut`
- `hackathons.json` → `app.schemas.hackathon.HackathonOut`

All four ship empty (`[]`). Add real content either by hand-editing these
files and redeploying, or through the admin dashboard (remembering the
caveat above).
