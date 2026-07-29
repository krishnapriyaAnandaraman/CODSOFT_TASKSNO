# CodSoft Cloud Computing Internship — Tasks 1, 2 & 3

This covers the **3 tasks** needed to complete the internship (you only
need 3 of the 5). Each task is a self-contained, tested Flask app with
its own detailed `README.md` — start there for setup steps.

| Folder | Task | Storage used |
|---|---|---|
| `task1_file_storage/` | Cloud File Storage System | AWS S3 |
| `task2_deduplication/` | Cloud Data Deduplication System | AWS S3 + SQLite index (SHA-256 hashing) |
| `task3_bus_reservation/` | Cloud-Based Bus Ticket Reservation System | SQLite (with a documented path to AWS RDS) |

Tasks 1 and 2 share the same AWS S3 bucket and IAM credentials — set
those up once (Task 1's README walks through it) and reuse them for
Task 2. Task 3 runs standalone with no AWS account required, but its
README also shows how to deploy it publicly (Render or AWS Elastic
Beanstalk) if you want a live demo link.

## Recommended order
1. **Task 1 first** — it's the simplest and gets your AWS account/bucket
   set up, which Task 2 depends on.
2. **Task 2 next** — it reuses the same bucket, just adds hashing + a
   duplicate check.
3. **Task 3 last** — no AWS dependency, but the most "features" (search,
   seat map, booking, cancellation), so budget the most time for it.

## Submission checklist (per the CodSoft slides)
- [ ] Update your LinkedIn profile
- [ ] Create ONE GitHub repo named exactly `CODSOFT_TASKSNO`
- [ ] Put each task in its own subfolder inside that repo (mirror this structure)
- [ ] Add a root-level README summarizing all 3 tasks (this file is a good starting point)
- [ ] `.gitignore` should exclude: `venv/`, `.env`, `*.db`, `__pycache__/`
- [ ] Record ONE video per task (or one combined video covering all 3),
      demoing the actual working app, and post it on LinkedIn
- [ ] Tag CodSoft in the post, add `#codsoft #internship #cloudcomputing`
- [ ] Fill out the task submission form (shared via email) with your repo link

## A tip on the demo video
Graders/recruiters skim these — lead with the working feature (upload
succeeding, duplicate rejected, seat booked) in the first 10 seconds
rather than a long intro. 60–90 seconds per task is plenty.
