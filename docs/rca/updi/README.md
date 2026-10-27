---
title: "Root cause analysis: Methods and examples"
source: "https://plane.so/blog/root-cause-analysis-what-it-is-methods-and-how-to-write-its-report"
published: 2026-04-01
created: 2026-10-26
description: "Understand root cause analysis with practical methods, step-by-step RCA techniques, and a structured root cause analysis report format."
thinking: "unltra effort think before doing and plan all please"
---
using all skills thinking example superpower focus on TDD please

## Current AVR128DA28 investigation — RCA_FRESH_01

[Latest rerun — 20261027T052038Z](../../../artifacts/updi/fresh/reruns/20261027T052038Z/STAR_RCA.md): P0/100 and Q99/100 strict SIB length passes, excluding smoke. User-confirmed P power change at unknown timing confounds causality. No repair; control/identity gates remain closed. Historical raw evidence is intact; two context-file hash drifts are documented.

[Fresh STAR RCA and evidence](../../../artifacts/updi/fresh/STAR_RCA.md): P and Q each failed 0/30 baseline SIB attempts after exact local echoes. The fresh runner is implemented and host-tested; causal isolation is blocked pending the simultaneous electrical capture specified in the report. No repair, flash/fuse write, erase or BOD change occurred. Historical investigation evidence remains separate and preserved.

## Introduction

Every team hits a point where something breaks: a missed deadline, a failed deployment, or a recurring [bug](https://plane.so/blog/bug-triage-process-how-to-run-it-and-what-to-prioritize). The instinct is to fix it fast and move on. But without a structured root cause analysis, the same problem resurfaces, often worse. RCA is the discipline of looking beyond symptoms to identify the root cause of a failure. This post covers the core methods, step-by-step process, and how to write an RCA report that your team can act on.

## What is root cause analysis?

Root cause analysis is the process of tracing a problem backward from its visible symptoms to the underlying condition that produced it, and then fixing that condition, not the symptom.

The distinction matters because symptoms and root causes look similar when you're moving fast. A missed deadline looks like an execution problem. A production regression looks like a testing gap. Repeated sprint spillover looks like a capacity problem. Each of those surface explanations might be partially true, but *where*, not *why,* it keeps happening.

Root cause analysis forces a different question: what condition in our system made this outcome predictable?

**What RCA is not:**

- A blame exercise. If your investigation ends with "person X made a mistake," you haven't found the root cause. You've found a symptom at the human layer. The real question is: what in the system made that mistake likely or inevitable?
- A post-mortem ritual. Post-mortems document what happened. RCA explains why. They often happen together, but the investigation work is distinct.
- A one-size process. The right method depends on the structure of the problem. A single-team workflow failure and a cross-functional production incident require different approaches.

## When RCA is worth running

Not every failure warrants a full investigation. Applying RCA to every bug or minor slip dilutes it into a compliance checkbox. The right trigger is a problem that's systemic, repeated, or high enough in impact that recurrence would be genuinely costly.

Run RCA when:

### Something happened more than once

If the same type of delay, miscommunication, or defect has appeared across multiple sprints or projects, it's a signal about your system, not about the people in it. One occurrence is an event. Two is a pattern worth investigating.

### 1\. A production incident had customer impact

Outages, data errors, and SLA breaches almost always involve a chain of contributing factors. A single fix won't break the chain; only understanding the chain does.

### 2\. A release missed a hard commitment

When a slip affects customers, partners, or downstream roadmap sequencing, the cost of recurrence is high enough to justify a structured investigation.

### 3\. A recurring process is consistently breaking

Sprint reviews where every team reports the same blocker. Handoffs that always generate rework. Planning cycles that consistently miss dependencies. These aren't execution failures — they're process design failures.

**Don't run RCA when** the failure was genuinely isolated, low-impact, and the corrective action is obvious. A typo in a config file that caused a one-time deployment failure, caught within minutes, is not an RCA candidate. Spending 90 minutes in an investigation meeting for that is theater.

## Root cause vs. contributing factor vs. symptom

Before choosing a method, get clear on the difference between these three things. Teams that conflate them produce weak findings.

1. **Symptom:** The visible signal that something went wrong. A missed deadline. A build failure. A spike in support tickets. Symptoms tell you *where* the system is hurting, not why.
2. **Contributing factor:** A condition that made the failure more likely but didn't directly cause it. Unclear requirements. A compressed timeline. An undocumented dependency. Contributing factors are real and worth capturing, but they're not the root cause.
3. **Root cause:** The primary condition that, if changed, would prevent the outcome from recurring. It's usually deeper than the first explanation, often structural, and often uncomfortable because it points at process or system design rather than a single person's decision.

A useful test: if you addressed the thing you've identified, would the same failure be unlikely to recur under similar conditions? If yes, you probably have a root cause. If you're not sure, keep asking why.

## How to choose the right RCA method

There is no universal RCA method. The right technique depends on whether the failure is linear or multi-branching, whether you have data, and whether it followed a known change. Here's how to route:

| Problem type | Best method |
| --- | --- |
| Linear failure chain, single team, clear sequence | 5 Whys |
| Complex, cross-functional, multiple contributing categories | Fishbone diagram |
| Problem appeared right after a release, deploy, or config change | Change analysis |
| Production incident with a timeline of events | Event analysis (timeline reconstruction) |
| Same issues keep recurring across many cycles, data available | Pareto analysis |

When in doubt, start with the 5 Whys. If you hit a fork — more than one equally plausible "why" — switch to a fishbone.

## The five RCA methods, explained with worked examples

### 1\. The 5 Whys

**How it works:** Take a precise problem statement. Ask "why did this happen?" Take the answer and ask why again. Continue until you reach a cause that is actionable and systemic rather than just describing a closer symptom.

Five is a guideline, not a rule. Some problems resolve in three iterations. Others need seven. The stopping condition is: does fixing this prevent recurrence under similar conditions?

**Worked example — missed release:**

> Problem: The v4.1 release slipped by four days, missing two enterprise customer commitments.

- Why did the release slip? The staging environment was unavailable for the final testing window.
- Why was staging unavailable? A configuration change had been applied to it without a scheduled maintenance window.
- Why was there no maintenance window? There was no documented protocol for environment changes during active release cycles.
- Why was there no protocol? The release process documentation was written when the team had four engineers and was never updated after the team scaled to twelve.
- **Root cause:** Process documentation didn't scale with team growth, leaving critical operational steps undocumented for half the team.

**Corrective action:** Audit all release process docs against current team size and workflow. Assign an owner for quarterly maintenance. Add an environment-change protocol with the required approvals during release windows.

**Where 5 Whys breaks down:** When a problem has multiple parallel causes, the linear structure misses branches. If you get to "Why?" and there are two equally valid answers, the fishbone is a better fit.

### 2\. Fishbone diagram (Ishikawa diagram)

**How it works:** Write the problem statement at the "head" of the diagram. Draw branches representing categories of potential causes. Within each category, add contributing factors. Then analyze which factors across categories are most likely to have combined to produce the failure.

For software and product teams, the most useful categories are:

- **People**: decisions, skill gaps, communication failures, unclear ownership
- **Process**: workflow steps that were missing, ambiguous, or misaligned
- **Tools**: tooling limitations, configuration gaps, missing automation
- **Environment:** infrastructure state, external dependencies, system conditions
- **Inputs:** requirements quality, specification clarity, dependency readiness

**Worked example: recurring defects escaping to production:**

> Problem: Three separate bugs that were marked "resolved" in QA were discovered by customers in the past two releases.

Fishbone branches might surface:

- *People:* No single QA owner for regression coverage. Engineers merging without a second review when deadlines are tight.
- *Process:* Definition of Done doesn't require regression testing on changed components. QA sign-off happens in parallel with staging deploy rather than before.
- *Tools:* Test suite doesn't auto-run on components affected by dependency changes. No coverage tracking across releases.
- *Environment:* Staging environment uses mocked dependencies that don't reflect production configurations.
- *Inputs:* Ticket acceptance criteria rarely specify which existing flows must not break.

Cross-referencing these branches reveals the actual pattern: there's no systematic way for QA to know which components to regression-test when a change lands, because there's no tooling support for dependency impact analysis and no process that requires engineers to surface it.

**Root cause:** The QA process assumes engineers will identify the regression scope, but there's no tooling or workflow checkpoint to make this reliable at speed.

**Corrective actions:** Introduce automated detection of dependency impacts in CI. Add a "regression scope" field to the release checklist, required before QA sign-off. Update the Definition of Done to include coverage sign-off on affected components.

### 3\. Change analysis

**How it works:** When a problem appeared shortly after a known change — a release, deploy, configuration update, team restructuring, tooling migration, or process change — compare system behavior before and after the change. The investigation focuses on what shifted and how that shift connects to the failure.

This method is faster than a full fishbone when the timing signal is strong. It works because most production incidents and regression defects have a trigger event. Change analysis helps you find it precisely.

**Worked example: post-deploy performance degradation:**

> Problem: API response times increased by ~300ms across key endpoints starting at 14:32 on Tuesday, 24 hours after the v3.8 deploy.

Change analysis questions:

- What changed in v3.8? Three backend services, two dependency version bumps, one database migration.
- What did not change? Frontend, authentication, infrastructure configuration.
- Which changes were made to the code path for the affected endpoints? One of the backend services handles the query layer for those endpoints.
- What specifically changed in that service? A new query was added that joins across two previously uncached tables.
- Did anything in the deployment environment change around the same time? A scheduled cache invalidation ran at 14:15, approximately 17 minutes before the spike appeared.

**Root cause:** The new join query was not benchmarked under production load conditions, and the cache invalidation exposed a cold-path performance gap that the dev environment hadn't surfaced.

**Corrective actions:** Add load-path benchmarking as a release requirement for query-layer changes. Add warm cache conditions to the staging environment. Require query plan review for any new database join above a defined table size.

### 4\. Event analysis (timeline reconstruction)

**How it works:** Reconstruct the incident as a precise chronological sequence using logs, system events, task transitions, communication records, and stakeholder inputs. Map each action, decision, and state change. Then identify where execution diverged from expectations and which specific condition at that moment influenced the outcome.

This is the standard method for production incidents, outages, and deployment failures, situations where something unfolded across multiple teams and systems over time, and the sequence of events matters as much as the individual causes.

**Worked example: service outage:**

> Problem: The payments service was unavailable for 23 minutes, affecting 1,200 active sessions.

Reconstructed timeline:

- 09:14: Routine infra maintenance window ends. Team marks complete.
- 09:22: Load balancer health check starts reporting intermittent failures on payments-service-02.
- 09:31: On-call engineer sees the alert. Initial read: transient, not escalated.
- 09:47: Error rate crosses threshold. Automated paging fires.
- 09:49: Engineer escalates. Determines payments-service-02 is failing to connect to the database.
- 09:52: Database connection pool is exhausted. Root investigation begins.
- 10:02: Team identifies that a config change during the 09:14 maintenance window set max\_connections to 10 instead of 100 (a digit transposition).
- 10:07: Config corrected, service restored.
- 10:07–10:37: Gradual session recovery.

What the timeline reveals: there were two windows where earlier action would have contained the blast radius — the 9-minute gap between the health check failure and on-call visibility, and the 16-minute gap between on-call visibility and escalation. The config error was human, but the response amplified it.

**Root cause:** No automated rollback exists for configuration changes to max\_connections. Manual config changes during maintenance windows have no pre-apply diff review. On-call response criteria for "intermittent" health check failures had no escalation threshold.

**Corrective actions:** Implement a config change diff review as a required maintenance-window step. Define and document escalation criteria for health check failure patterns. Add automated rollback for connection pool configurations below a defined threshold.

### 5\. Pareto analysis

**How it works:** When you have recurring issues across many cycles — not a single failure, but a pattern, Pareto analysis helps you identify which causes account for the majority of your problem volume. The logic: roughly 80% of failures come from roughly 20% of causes. Find that 20% and you get disproportionate improvement leverage.

This method requires data. It works best when your team has consistent issue tracking, incident logs, or bug categorization that lets you count cause frequency across a defined period.

**Worked example: sprint spillover pattern:**

> Problem: The team has carried over incomplete work in 9 of the last 12 sprints.

Tracking root causes across those 9 spillover sprints reveals:

- Dependency on external team not met in time: 7 occurrences
- Scope added after sprint start: 6 occurrences
- Underestimated complexity: 5 occurrences
- Unplanned oncall/incident response: 3 occurrences
- Tooling/environment issues: 2 occurrences
- Other: 2 occurrences

Total: 25 cause instances across 9 sprints. The top two causes (external dependencies, late scope additions) account for 13 of 25 — 52% of all spillover causes.

**Root cause priority:** Dependency readiness and scope control are the highest-leverage fixes. Improving estimation would help less than fixing the process around what enters the sprint and how external dependency commitments are tracked.

**Corrective actions:** Add a dependency readiness check as a sprint planning entry criterion. Freeze sprint scope at planning unless escalated. Set a defined SLA with the external team for dependency delivery dates, tracked in Plane as linked work items with status visibility.

## How to run an RCA: the actual process

Choosing a method is step two. Here's the full sequence:

### Step 1: Write a precise problem statement

This is not optional. Vague problem statements produce vague findings. A good problem statement includes: what happened, when, what was affected, and the measurable impact.

Weak: "The release was delayed." Strong: "The v4.1 release missed its July 3 deployment window by four days, blocking two enterprise onboardings and delaying three dependent feature rollouts by an estimated two sprints."

The problem statement anchors everything. Every "why" should connect back to it.

### Step 2: Collect evidence before forming a hypothesis

The most common RCA failure mode is arriving at the investigation meeting with a conclusion and using the process to confirm it. Evidence collection happens first, and it should be exhaustive:

- Deployment logs, error logs, system metrics from the failure window
- Linked work items, tickets, pull requests, and commit history
- Timeline of decisions and communications in the relevant channels
- Perspectives from everyone who touched the work — engineers, QA, PM, on-call

In Plane, this means pulling the full issue history for relevant work items: status transitions, comments, linked cycles, and any blocked/blocking relationships. That thread is usually the most complete record of how the work actually moved.

### Step 3: Map contributing factors before narrowing to root cause

List every condition that made this failure more likely. Don't filter yet. The point of this step is to build a complete picture of the execution environment before you start deciding which factor was primary. Skipping this step is why teams settle on the first plausible explanation rather than the real one.

### Step 4: Select your method and investigate

Use the routing table above. Run the method. Follow every branch.

### Step 5: Validate before you conclude

Test the finding: if the root cause you've identified had been different, would the outcome have been different? Trace the causal chain forward. Does it hold against the evidence? Can you identify the moment in the timeline where this cause created the conditions for failure? If not, keep investigating.

### Step 6: Define corrective actions that address the cause, not the symptom

Every corrective action should change something structural. "Be more careful" is not a corrective action. "Add a required dependency readiness checkbox to sprint planning" is.

Each action needs an owner, a due date, and a way to verify completion. If you're using Plane, these become work items, assigned, dated, and trackable like any other deliverable. This is the step that separates investigations that produce change from ones that produce documents.

### Step 7: Monitor whether the fix worked

Schedule a follow-up review, typically one or two cycles after implementation. Check whether the failure pattern has changed. If it hasn't, the investigation either found the wrong root cause or the corrective action wasn't implemented correctly. Either way, you have new information.

## How to write an RCA report

A good RCA report is a structured decision record, not a narrative essay. It should be short enough to read in ten minutes and specific enough that someone who wasn't in the room can understand what happened, why, and what changed.

Here's the structure, with what each section should actually contain:

1. **Problem summary**: What happened, when, which systems or workflows were affected, measurable impact. Two to three sentences. If it takes more than a paragraph, it's not a summary.
2. **Impact assessment**: Effects on delivery timelines, customer commitments, service reliability, or downstream work. Quantify where possible. This section justifies the investment in investigation.
3. **Timeline**: Chronological sequence of events leading to and through the failure. Include state changes, key decisions, alerts, handoffs. This is especially important for incidents involving multiple teams.
4. **Investigation method**: Which method you used and why. One sentence each. This matters for reproducibility across future investigations.
5. **Evidence reviewed**: Logs, metrics, linked issues, stakeholder inputs, communication records. Not a narrative — a list. This is what makes findings auditable.
6. **Contributing factors**: The conditions that influenced the failure. Specific, not generic. "Unclear requirements" is not a contributing factor. "Acceptance criteria for the payment flow were approved two days before implementation, after scoping was complete, leaving no time for clarification" is.
7. **Root cause:** One to three sentences. Direct. The explanation of why the failure happened at the system level and why fixing this prevents recurrence.
8. **Corrective actions**: A table. Columns: action, owner, due date, status. Each action should be specific enough that there's no ambiguity about whether it's done.
9. **Preventive actions**: What changes to processes, tooling, or workflows reduce the likelihood of similar failures in other areas? Unlike corrective actions, preventive actions fix the trigger; corrective actions reduce the risk class.
10. **Follow-up review date**: When will you check whether the fixes worked? Put a date in the doc before you close it.

## What weak vs. strong corrective actions look like

This is where most RCA reports lose their value. Weak corrective actions describe intentions. Strong ones describe changes.

| Weak | Strong |
| --- | --- |
| "Improve team communication" | "Add a cross-team dependency standup every Monday at 10am. Owner: \[PM\]. Start date: \[date\]." |
| "Write better documentation" | "Add a required architecture decision record (ADR) for all changes to shared services. Template to be added to the repo. Owner: \[tech lead\]. Due: \[date\]." |
| "Be more careful during releases" | "Add a pre-release checklist to the deployment runbook with a required max\_connections verification step. Owner: \[infra lead\]. Due: \[date\]." |
| "Address testing gaps" | "Add automated regression coverage for all components with cross-service dependencies, tracked in CI. Owner: \[QA lead\]. Due: \[date\]." |

The test: could someone pick this action up six weeks from now with no context and know exactly what to do? If not, it's not specific enough.

## Common mistakes that make RCA useless

Most RCA efforts fail not during the investigation but afterward, when findings remain vague, corrective actions go unowned, and the same failure reappears two sprints later. The mistakes below are not about effort or intent. They are about the structural shortcuts that make investigations feel complete while leaving the underlying condition untouched.

### 1\. Stopping at the first plausible answer

The first explanation is almost always a symptom at a different layer. The staging environment was unavailable — but why? The config was wrong — but why was there no review step? Depth is the entire point.

### 2\. Treating "human error" as a root cause

Humans make mistakes in poorly designed systems. When an investigation ends with "engineer X didn't follow the process," the real finding is that the process relies on individual vigilance under pressure rather than structural enforcement. The corrective action points at the system, not the person.

### 3\. Running the investigation with the people who built the thing

The team closest to the work has the deepest context but the strongest pre-existing explanations. Invite someone from outside the immediate team to challenge assumptions during the investigation.

### 4\. Writing corrective actions without assigning owners

Unowned actions don't get done. Every item needs a name, a date, and a place in someone's actual work queue. In Plane, that means a work item with an assignee and a due date, in a cycle the owner is actively tracking.

### 5\. Closing the report without scheduling a follow-up

The report is not the outcome. The outcome is the system no longer failing that way. Schedule the follow-up before you close the doc.

## Final thoughts

Root cause analysis is not a post-mortem ritual or a process compliance requirement. It is one of the most practical tools a team has for building systems that fail less over time, but only when the investigation goes past the first plausible explanation, the findings get documented with enough specificity to be acted on, and someone actually checks whether the fix worked.

Treat RCA as a standard practice, not an emergency response. Consistent tracking shifts teams from firefighting to prevention, compounding into a more resilient system. The real ROI isn’t in the documentation; it’s the six-month reality of never having to fix the same problem twice.

## Frequently asked questions

### Q1. What are the 5 steps of root cause analysis?

The five basic steps of root cause analysis are:

1. **Define the problem** by describing what happened and its impact.
2. **Collect evidence** such as timelines, logs, and stakeholder inputs.
3. **Identify the root cause** using methods like the 5 Whys or a fishbone diagram.
4. **Develop corrective actions** that address the underlying cause.
5. **Monitor results** to verify the solution prevents the issue from recurring.

### Q2. What are the 5 core principles of RCA?

The five core principles of root cause analysis are:

1. Focus on the root cause rather than the symptom.
2. Investigate systems and processes instead of assigning blame.
3. Use evidence to support findings.
4. Consider all contributing factors before reaching a conclusion.
5. Turn findings into corrective and preventive actions that reduce recurrence.

These principles help teams perform accurate and repeatable investigations.

### Q3. Is RCA part of Six Sigma?

Yes. **Root cause analysis (RCA)** is a key technique used in **Six Sigma**, particularly during the **Analyze** phase of the DMAIC framework. Teams use RCA to identify the underlying causes of defects, process variation, and operational issues before implementing improvements. RCA is also widely used outside Six Sigma in project management, software development, manufacturing, healthcare, and IT operations.

### Q4. What are the 7 steps of root cause analysis?

The seven steps of root cause analysis are:

1. Define the problem.
2. Collect data and evidence.
3. Identify contributing factors.
4. Determine the root cause.
5. Develop corrective actions.
6. Implement the solution.
7. Review the results to confirm the issue has been resolved and prevent recurrence.

Many organizations adapt these steps based on the complexity of the problem.

### Q5. What are the 6 steps of RCA?

A common six-step root cause analysis process includes:

1. Define the problem.
2. Gather evidence and context.
3. Analyze contributing factors.
4. Identify and validate the root cause.
5. Implement corrective actions.
6. Monitor outcomes and document lessons learned.

This framework helps teams resolve recurring issues and continuously improve their processes.

![Plane](https://plane.so/_next/image?url=%2Fhome%2Fv4%2Fcta%2Fbg.webp&w=3840&q=75&dpl=dpl_8xva6VS6tJf4rfr5xBKF3Kbq1B9u)

### Every team, every use case, the right momentum

Hundreds of Jira, Linear, Asana, and ClickUp customers have rediscovered the joy of work. We’d love to help you do that, too.

Thinking first please and show first principle

