# Software Requirements Specification (SRS)
## Online Attendance Management System

**Client context:** Sankar Matriculation School, Sankagiri West, Namakkal District, Tamil Nadu  
**Version:** 1.0 project draft  
**Status:** Academic prototype; review with school stakeholders before operational use.

## 1. Purpose
Provide an online, browser-accessible application for authorized school staff to maintain student records, record attendance, and generate attendance reports.

## 2. Scope
The system supports administrator and teacher accounts, class/section setup, student management, attendance for a selected date, date-range reports, attendance percentages, filtering, and CSV export. The current prototype does not provide parent/student logins, timetable integration, SMS notifications, or official student-information-system integration.

## 3. User classes
- **Administrator:** manages accounts, classes/sections, subjects, students, and reports.
- **Teacher:** views assigned classes, marks attendance, and views reports for assigned classes.

## 4. Functional requirements
- FR-01: Users can authenticate with a username and password.
- FR-02: Admin can create and deactivate user accounts.
- FR-03: Admin can create classes and sections and assign classes to teachers.
- FR-04: Admin can add, update, search, and archive student records.
- FR-05: Admission numbers must be unique.
- FR-06: Authorized teachers/admins can mark each active student Present, Absent, or Leave for a date.
- FR-07: Saving attendance updates an existing record for the same student/date instead of creating a duplicate.
- FR-08: Users can filter reports by date range, class, student name, or admission number.
- FR-09: Reports show marked, present, absent, and leave days, and attendance percentage.
- FR-10: Users with permission can export filtered report results to CSV.
- FR-11: Teachers can access only classes assigned to their account.
- FR-12: The app exposes a health-check endpoint for hosting checks.

## 5. Non-functional requirements
- NFR-01 Portability: use a standards-based web interface and avoid device-specific installation.
- NFR-02 Compatibility: test current Chrome, Edge, Firefox, Safari, and mobile browsers where available.
- NFR-03 Responsiveness: interface adapts to phone, tablet, and desktop screen sizes.
- NFR-04 Security: password hashes, role checks, parameterized SQL, validation, HTTPS in production, and secure session-cookie settings.
- NFR-05 Reliability: unique constraints prevent duplicate attendance for the same student/date.
- NFR-06 Performance: ordinary class attendance and date-range reports should respond promptly for the agreed school dataset.
- NFR-07 Maintainability: routes, templates, static assets, schema initialization, and tests are separated.
- NFR-08 Cost: use open-source application components and free tiers where practical; persistent storage may require a paid service.
- NFR-09 Privacy: use only approved data, minimize access, and maintain verified backups.

## 6. Attendance calculation
For a chosen date range:
`Attendance percentage = Present days / Marked days × 100`.
A Leave record is counted as a marked day but not as Present. Unmarked dates are excluded. Confirm this policy with the school because institutions may define leave and working-day percentages differently.

## 7. Data model
- users(id, username, full_name, password_hash, role, active, created_at)
- classes(id, name, section)
- students(id, admission_no, full_name, class_id, active, created_at)
- subjects(id, name)
- teacher_classes(teacher_id, class_id)
- attendance(id, student_id, attendance_date, status, marked_by, updated_at)

## 8. Constraints and assumptions
- Reliable internet and a supported browser are available.
- The school provides approved class, section, subject, and user lists.
- The prototype uses SQLite. Concurrent-write scale and hosting persistence must be evaluated before real use.
- Hosting free-tier terms may change; verify them at deployment time.
- A production release requires CSRF protection, login rate limiting, a password reset/change process, tested backups, and security/privacy review.

## 9. Acceptance criteria
- Authorized admin and teacher can log in; invalid credentials are rejected.
- Teacher cannot access admin-only pages or unassigned classes.
- Admin can create a class and student; duplicate admission number is rejected.
- Attendance saves and can be edited for the same date without duplicate rows.
- Reports and CSV export reflect saved records and filters.
- UI remains usable on desktop and mobile widths.
- Deployment and backup/restore steps are documented and demonstrated.
