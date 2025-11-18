---
name: italian-grammar-advisor
description: "Provides A2→B2 Italian grammar progression guidance tailored for French speakers. Activated when selecting grammar topics for lessons, explaining grammar concepts, or determining appropriate difficulty level based on student's current learning phase."
---

# Italian Grammar Progression Advisor

## When to Use This Skill

**Activate when Maestra needs to:**
- Select appropriate grammar topic for lesson (e.g., Monday grammar focus)
- Explain why a specific grammar concept is relevant to current level
- Determine if a grammar topic is premature or timely
- Provide French→Italian contrastive explanation
- Plan grammar progression across the week/month

**Do NOT activate for:**
- Vocabulary selection (integrated in core teaching)
- Pronunciation guidance (use pronunciation-coach skill)
- Speaking practice execution (use speaking-coach skill)
- General conversation flow

---

## Quick Reference: 4-Phase Progression

| Phase | Timeframe | Level | Grammar Focus | Key Transition |
|-------|-----------|-------|----------------|-----------------|
| **Phase 1** | Weeks 1-5 | A2 | Past tense mastery (passato prossimo/imperfetto) | A2→B1 gateway |
| **Phase 2** | Weeks 6-17 | B1 | Subjunctive introduction (present subjunctive basics) | Mood introduction |
| **Phase 3** | Weeks 18-22 | B1+ | Subjunctive consolidation (imperfect/pluperfect) | Complex subjunctive |
| **Phase 4** | Weeks 23-33 | B2 | Subjunctive mastery + conditional chains | B2 fluency |

---

## Decision Logic: What Topic Today?

### Step 1: Determine Current Phase
Based on memory of learning journey:
- Has student mastered passato prossimo/imperfetto distinction? → Past Phase 1
- Can student recognize present subjunctive? → Within Phase 2+
- Does student struggle with imperfect subjunctive? → Phase 3
- Is student working on conditional chains? → Phase 4

### Step 2: Select Topic Strategy

**If in Phase 1 (A2)**:
Priority sequence:
1. **Passato Prossimo** - foundation, then
2. **Imperfetto** - contrast with prossimo, then
3. **Passato Prossimo vs. Imperfetto** - integration

French speaker note: Passé composé/Imparfait distinction exists in French, but auxiliary selection differs (French: avoir default, Italian: essere/avere depends on verb). Emphasize this transfer difference.

**If in Phase 2 (early B1)**:
Priority sequence:
1. **Present Subjunctive Formation** - structure first, then
2. **When to Use Present Subjunctive** - context + emotions/opinions/doubt, then
3. **Common Subjunctive Triggers** - after certain conjunctions

French speaker note: French subjunctive exists (French: je veuille que tu parles). Italian subjunctive has MORE triggers. Use French as foundation, show expanded usage.

**If in Phase 3 (B1+)**:
Priority sequence:
1. **Imperfect Subjunctive** - historical context shifts, then
2. **Conditional Sentences** - si + imperfect subjunctive combinations, then
3. **Pluperfect Subjunctive** - complex past narratives

French speaker note: French has passé du subjonctif (similar to pluperfect). Show parallel structure.

**If in Phase 4 (B2)**:
Priority sequence:
1. **Subjunctive vs. Infinitive** - nuanced register differences, then
2. **Conditional Chains** - complex hypotheticals, then
3. **Register-Specific Subjunctive** - formal narratives

---

### Step 3: Frame the Lesson

For chosen topic, provide to core agent:

```
**Grammar Topic**: [Topic]
**Level**: [Phase X]
**French Parallel**: [How this works in French, or "No direct parallel"]
**Core Challenge for Your Student**: [Key difficulty specific to her]
**Lesson Flow**:
1. [Activate memory: What has she already learned about this?]
2. [Start with French comparison to build on existing knowledge]
3. [Present formation/concept with 3-4 examples]
4. [Practice with her context (Varese, interests, real situations)]
5. [Check understanding with contrast exercise]
```

---

## Critical Warnings

⚠️ **Don't jump topics**: If student hasn't mastered passato prossimo/imperfetto distinction, subjunctive will be frustrating. Master tense sequencing.

⚠️ **French transfer cuts both ways**: Subjunctive exists in French, so she has foundation. But Italian uses it MORE. Show the expansion, don't assume transfer.

⚠️ **Assess mastery via conversation**: Don't test formally on Friday. Assess naturally: Can she use past tenses in conversation? Does she automatically recognize subjunctive triggers?

---

## For Detailed Reference

See `references/grammar_progression_matrix.md` for:
- Full A2→B2 progression matrix (all tenses/moods)
- Common error patterns by phase
- Example bank indexed by topic + level + context
- French→Italian contrastive grammar notes
- Assessment indicators for phase mastery
