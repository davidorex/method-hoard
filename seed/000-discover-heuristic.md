---
id: 0
slug: discover-heuristic
title: Discover Heuristic — What Makes a Method Hoard-Worthy
problem: Determining which techniques from recent work are generalizable enough to stock in the hoard, without the hoard becoming uselessly full or missing truly valuable methods
language: prose
tags: [meta, heuristic, discovery, curation]
source: method-hoard
created: 2026-03-01
updated: 2026-03-01
retrievals: 0
---

## Method

When reflecting on recent work to discover hoard-worthy methods, apply these criteria:

**Stock when:**
- The technique transfers beyond this project's domain — it solves a kind of problem, not just this instance
- A non-obvious solution was found after struggle — the kind of thing that would be painfully rediscovered
- Multiple tools or libraries were combined in a way that isn't well-documented elsewhere
- The same kind of problem recurs across projects (data transformation, CLI scaffolding, auth flows, search indexing, configuration patterns, etc.)
- The approach is better than the obvious/common one and that difference matters in practice

**Don't stock when:**
- It's domain-specific business logic that only makes sense in one project
- It's a trivial use of a well-documented API — the official docs are the method
- It's project-specific configuration with no transferable insight
- It's a one-off workaround for a specific bug
- It's already well-represented in the hoard (check with search first)

**How to extract a method:**
1. Name the problem it solves — what situation triggers reaching for this technique
2. Describe the method — the how, at the level of a technique, not just the what
3. Include working code — enough to demonstrate the method, not an entire application
4. Capture context — why this approach, what was considered and rejected, what the trade-offs are
5. Tag it — by problem domain, language, and technique type so future search can find it

**Calibration signals:**
- If the hoard keeps surfacing items nobody reaches for → the bar is too low, tighten the criteria
- If techniques keep being rediscovered that should have been hoarded → the bar is too high, loosen the criteria
- If search results are noisy → methods need better problem descriptions and tags
- If methods are too abstract to use → they need more concrete code and context
- If methods are too specific to reuse → they need the project-specific parts stripped out

This heuristic is itself revisable. Update it based on what the hoard's actual usage patterns reveal.

## Code

```python
# No executable code — this is a prose method.
# The discover agent reads this item and applies it as judgment criteria
# when reflecting on recent work to identify generalizable methods.
```

## Context

This is hoard item zero — the self-bootstrapping element. The method-hoard system starts with this heuristic as its first item. The heuristic governs what gets added to the hoard, and is itself subject to revision based on how well the hoard serves its purpose. It contains the criteria for what's hoard-worthy, patterns for how to extract and describe methods so future agents can use them, and calibration signals for adjusting the bar over time.
