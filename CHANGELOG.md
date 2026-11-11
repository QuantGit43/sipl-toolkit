# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/), версії — [SemVer](https://semver.org/lang/uk/).

## [0.1.0] - 2026-11-18

### Додано
- Формальна граматика SIPL (Lark) за БНФ курсу, лексика, коментарі `//`, ASCII-форми `or`/`not` (CORE-01).
- Парсер у власне типізоване AST із `SourceSpan`; діагностика з рядком/колонкою та підказками (CORE-02).
- Інтерпретатор: стан, присвоювання, `;`, `if`, `while`, `begin/end`, `skip`; ліміт кроків (CORE-03).
- Подієва модель виконання і trace: before/after, зміна змінної, перевірка умови, завершення (CORE-04).
- CLI `sipl parse|check|run|trace|term|tree` зі стабільним JSON-конвертом (CORE-05).
- Дерево синтаксичного виводу: text, JSON, DOT, SVG; нумерація листків і перевірка обходу (VIS-01).
- Семантичний терм у нотації курсу, ланцюжок перетворень і журнал правил NS_*; text/LaTeX/JSON (SEM-01).
- Розширення VS Code: підсвітка, коментарі, дужки, відступи, сніпети (IDE-01).
- CI (ruff + pytest + збірка пакета і .vsix), реліз за тегом (REL-01, REL-02, REL-03).

[0.1.0]: https://github.com/QuantGit43/sipl-toolkit/releases/tag/v0.1.0
