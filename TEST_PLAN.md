# Test Cases and Results Template

Run automated tests with `pytest`. Record manual browser/device tests after deployment. The results below are expected outcomes, not a claim that every deployment/browser has already been tested.

| ID | Scenario | Steps | Expected result | Result |
|---|---|---|---|---|
| TC-01 | Valid admin login | Sign in with admin demo account in local demo | Dashboard appears | Pending local run |
| TC-02 | Invalid login | Submit wrong password | Generic invalid-credentials message; no login | Pending local run |
| TC-03 | Teacher role boundary | Sign in as teacher, visit `/users` | HTTP 403 page | Pending local run |
| TC-04 | Add student | Admin creates student with valid unique admission number | Student appears in directory | Pending local run |
| TC-05 | Duplicate admission number | Add a student with an existing admission number | Friendly validation error; no duplicate | Pending local run |
| TC-06 | Mark attendance | Select class/date, choose status for every student, save | Saved statuses appear when reloaded | Pending local run |
| TC-07 | Edit attendance | Change a student's status for same date and save | Existing row updates; no duplicate | Pending local run |
| TC-08 | Future date | Attempt to submit attendance for a future date | Submission rejected | Pending local run |
| TC-09 | Report calculation | Mark 3 Present, 1 Absent, 1 Leave | Percentage is 60% (3 / 5) | Pending manual test |
| TC-10 | CSV export | Apply filters and export | CSV matches report filters | Pending manual test |
| TC-11 | Teacher class access | Teacher opens an unassigned class ID | HTTP 403 | Pending manual test |
| TC-12 | Mobile layout | Open on a phone-sized viewport | Forms and tables remain usable | Pending manual test |
| TC-13 | Browser portability | Test Chrome, Edge, Firefox, Safari if available | Core workflows work in each tested browser | Pending manual test |
| TC-14 | Backup and restore | Backup DB, restore to isolated instance, verify records | Records are intact | Pending operational test |
| TC-15 | Hosting sleep/restart | Redeploy/restart hosted app | Health check succeeds; data persists only with configured persistent storage | Pending deployment test |

## Automated test command

```bash
pip install pytest
pytest -q
```

## Portability test report template
Record device, OS, browser/version, viewport, date, test IDs, pass/fail, screenshots, and issues. Do not mark a platform passed unless it was actually tested.
