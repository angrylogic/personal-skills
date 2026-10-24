---
name: recap
description: Review human-corrected mistakes in the current conversation and propose changes to architecture, interfaces, linters, or review instructions that would prevent recurrence. Use when asked to recap mistakes or learn from corrections in a session.
---

# Recap

Turn human corrections in the current conversation into concrete prevention
proposals. Produce the proposals in chat; implementation is a separate task.

## 1. Establish the evidence

Read the available conversation from the beginning. For each candidate mistake,
identify the agent's action or claim, the human's correction, and the requirement
or information available before the mistake. Use a short quote or precise
paraphrase to locate the exchange; invent neither quotes nor message identifiers.

A finding requires evidence that the human corrected an actual error. New
requirements, changed preferences, ordinary clarification, and errors the agent
found unaided are outside this recap. When the distinction is uncertain, omit the
candidate rather than label the human's new information an agent failure.

Group corrections with the same underlying cause into one finding, retaining
the supporting exchanges. Distinguish the observed failure from a hypothesized
cause. If history is truncated or summarized, state the coverage limit and use
only corrections supported by the available record.

Finish this step when every visible human correction has been assessed and each
retained finding has both the mistaken behavior and its correction as evidence.
If none qualify, say so and finish without manufacturing lessons.

## 2. Find the strongest practical prevention

Inspect the relevant implementation, interfaces, lint configuration, and review
instructions. Check whether the correction has already been addressed, and
whether an existing safeguard would have caught it if used. Prefer repairing or
connecting that safeguard over adding a duplicate. Keep already-addressed
findings visible and identify any remaining gap.

Evaluate these options in order for each cause:

1. **Architecture or interfaces:** remove the opportunity for the mistake by
   changing ownership, centralizing an invariant, constraining inputs, or making
   invalid states unrepresentable. For module or seam design, read
   [codebase-design](../codebase-design/SKILL.md). Name the affected interface and
   explain how the original mistaken action becomes impossible or fails early.
2. **Linters:** when a structural fix is impractical or leaves a gap, propose a
   deterministic check. Name the existing tool or smallest new rule, its scope,
   diagnostic, and where it runs. Give a failing example modeled on the mistake
   and a valid example that should pass. Explain false positives or limitations;
   reserve judgment-dependent questions for review.
3. **Review instructions:** for the remaining judgment-dependent gap, propose a
   focused review reference and a pointer from the review instructions actually
   used by this project. Specify the trigger for reading it, the concrete check,
   and the evidence a reviewer should inspect. Reuse an existing reference when
   possible; write the proposed wording rather than saying "update the docs."

Select the strongest practical option. Add another layer only when it covers a
different remaining gap. Explain briefly why earlier options are insufficient
when recommending a later one. Scale the change to the demonstrated failure;
generic reminders to be careful are not prevention mechanisms.

## 3. Present proposals

For each finding, give:

- **Correction:** the mistaken behavior and the human's correction, with evidence.
- **Cause:** the mechanism that allowed it; label uncertainty explicitly.
- **Proposal:** the recommended change, concrete target, and why this level fits.
- **Verification:** replay the original mistake against the proposed safeguard;
  explain the expected rejection or review finding and a valid case it permits.
- **Status:** already addressed, partially addressed, or proposed; include any
  remaining gap, cost, or trade-off material to the decision.

Order proposals by likely recurrence and impact, using evidence rather than
invented scores. End with which change to tackle first and why. Keep the result
in chat: invocation authorizes investigation and proposals, not edits, new lint
rules, saved reports, tickets, commits, or publication. Implement only when the
human subsequently asks for that work.
