# Prompt Improver: an AI prompt engineering skill

**Turn a rough idea into a clear, testable task for an AI model.** Prompt Improver asks useful questions, researches missing context when tools are available, and produces a prompt you can copy into a new conversation. You decide when the briefing ends.

[Русский](README.md) · **English**

[![Version 1.1.1](https://img.shields.io/badge/version-1.1.1-173F46)](project.json) [![Markdown](https://img.shields.io/badge/format-Markdown-53616B)](skill/prompt-improver/SKILL.md) [![18-topic audit](https://img.shields.io/badge/evaluation-18%20topics-173F46)](evals/AUDIT-2026-09-06.md)

The skill and portable specification are written in Russian. Their instructions ask the model to use the user's language. This English page documents usage; comparable performance in English or across different models has not been established.

## Install in Codex

With Node.js and `npx` available:

```bash
npx skills add saymonseo/prompt-improver --skill prompt-improver --agent codex --global
```

Repository discovery was checked with [Skills CLI](https://github.com/vercel-labs/skills) 1.5.23. Review any local modifications before replacing an existing installation.

Once your environment has loaded the skill, start with:

```text
$prompt-improver Help me prepare a prompt for an online store.
```

For manual installation, copy the complete [skill/prompt-improver folder](https://github.com/saymonseo/prompt-improver/tree/main/skill/prompt-improver), including `references` and `agents`, into `$CODEX_HOME/skills` or `~/.codex/skills` when `CODEX_HOME` is unset.

## Use with ChatGPT, Claude, or another model

Attach [SPECIFICATION.md](SPECIFICATION.md), or paste its contents if attachments are unavailable. Then send your task separately:

```text
Use the specification as instructions for helping me define a task for AI.
Clarify my goal and prepare a prompt I can use in a new conversation.
My task: [describe what you want].
```

The specification includes all instruction modules. File support, browsing, and instruction following depend on the host environment. The project supplies instructions, not model access or an API service.

## How the briefing works

1. The assistant extracts the goal, constraints, and known information.
2. It asks one question or a small group of related questions.
3. After your answer, it previews the next topic and offers to continue or produce the prompt.
4. When you ask it to finish, it includes unresolved requirements in the final prompt.

“Skip this topic” does not end the briefing. “I don't know” calls for help understanding the choice. “Choose for me” delegates a decision within its scope. “No questions, just the prompt” skips the interview.

## What it supports

The project includes domain guidance for software, construction, and automotive tasks, plus a general profile for other fields. Task profiles cover research, calculations, planning, editing, teaching, and creative work.

For example, an online-store briefing can establish the catalog size, product variants, delivery area, order workflow, content sources, hosting, and maintenance responsibilities. These details come from answers or verified context; the assistant must not invent them from “build a store.”

## Evidence and uncertainty

The instructions distinguish user reports, sourced facts, calculations, hypotheses, assumptions, and unknowns. They require relevant sources when factual verification matters, and keep critical caveats inside the copyable prompt. If the model cannot browse or run a check, it must state that limitation.

These are behavioral instructions, not a guarantee of factual accuracy.

## Evaluation

The [18-topic audit](evals/AUDIT-2026-09-06.md) publishes briefing records and final prompts. The [role comparison](evals/ROLE-AB-2026-09-06.md) contains 36 fresh executions with two independent model reviews of each pair. Both reviewers found no substantial difference in 17 pairs; they disagreed on the science review.

This was one execution per condition in one configuration, not a representative benchmark. The project does not claim a measured accuracy increase or superiority over competing skills. Reports are in Russian.

## Project documentation

- [Development and validation](CONTRIBUTING.md)
- [Competitor review and proposed improvements](docs/COMPETITIVE-REVIEW-2026-09-06.md)
- [GitHub discoverability](docs/DISCOVERABILITY.md)
- [Evaluation protocol](evals/PROTOCOL.md) and [validation status](evals/VALIDATION.md)
- [Skill entrypoint](skill/prompt-improver/SKILL.md) and [portable specification](SPECIFICATION.md)

To report a problem, [open an issue](https://github.com/saymonseo/prompt-improver/issues) with an anonymized request, actual response, expected behavior, and environment details.
