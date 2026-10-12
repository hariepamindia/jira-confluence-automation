# Weekly Stakeholder Status Report

**Project:** Northstar Customer Portal (fictional example)  
**Reporting period:** 2026-10-05 – 2026-10-11  
**Prepared by:** Northstar delivery team  
**Report date:** 2026-10-12

## Project Health

**Status:** Yellow  
**Why:** Core portal work remains on track, but the identity-provider integration is blocked on a partner test credential. The team expects to recover the schedule if access is provided by October 14.

## Summary

- **Completed this period:** 8 issues, including profile editing and account recovery improvements
- **In progress:** 12 issues, including accessibility fixes and portal analytics
- **Blocked:** 1 issue — identity-provider integration test
- **At risk:** 2 issues — integration validation and final security review
- **Due soon / overdue:** 1 overdue item — partner test credential, originally due October 9

## Highlights

- Released profile editing to the staging environment and completed product-owner review.
- Resolved 6 high-priority accessibility findings; keyboard navigation now passes the agreed smoke checks.

## Risks and Blockers

| Risk or blocker | Impact | Owner | Mitigation / next step | Target date |
|---|---|---|---|---|
| Partner test credential has not been provided; integration testing is blocked. | Could delay end-to-end validation by up to three business days. | Partner team | Escalate the request; use the mock identity provider for other test cases while waiting. | 2026-10-14 |
| Security review has limited reviewer availability. | Findings may arrive too late for the planned release candidate. | Security lead | Reserve a review slot and submit the current build and checklist in advance. | 2026-10-16 |

## Milestones

| Milestone | Target date | Status | Progress / update |
|---|---|---|---|
| Feature complete | 2026-10-23 | On track | Profile and account recovery features are in staging; remaining work is in progress. |
| End-to-end validation | 2026-10-16 | At risk | Most scenarios are ready; identity-provider testing depends on the overdue credential. |

## Next Period: Planned Actions

| Action | Owner | Due date |
|---|---|---|
| Obtain the partner test credential and run the identity-provider test suite. | Integration lead | 2026-10-14 |
| Complete the reserved security review and triage any findings. | Security lead | 2026-10-16 |
| Finish the remaining accessibility fixes and rerun smoke checks. | Frontend lead | 2026-10-15 |

## Decisions or Support Needed

- Leadership help is requested to escalate the overdue test-credential request with the partner by 2026-10-13. Without access by 2026-10-14, the team will provide an updated end-to-end validation forecast.
