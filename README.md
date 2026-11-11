# SIPL Language Toolkit

[![CI](https://github.com/QuantGit43/sipl-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/QuantGit43/sipl-toolkit/actions/workflows/ci.yml)

Набір інструментів для мови SIPL з курсу «Теорія програмування»: парсер, інтерпретатор
з trace, дерево синтаксичного виводу, семантичні терми в нотації курсу, CLI та підсвітка
синтаксису для VS Code.

Проєктна робота: Саплюков Юрій, ТК-32.

## Обрані завдання

| ID | Завдання | Бали | Де реалізовано |
|---|---|---|---|
| CORE-01 | Формальна специфікація SIPL (Lark), позитивні/негативні тести | 0.5 | `src/sipl/grammar/sipl.lark`, `grammar/`, `tests/test_grammar.py` |
| CORE-02 | Парсер і типізоване AST з `SourceSpan`, діагностика | 1.5 | `src/sipl/parser.py`, `src/sipl/ast.py` |
| CORE-03 | Інтерпретатор: стан, `:=`, `;`, `if`, `while`, `begin/end`, `skip`, ліміт кроків | 2.0 | `src/sipl/interpreter/` |
| CORE-05 | CLI `parse/check/run/trace` + JSON-режим | 1.0 | `src/sipl/cli.py`, `docs/json-format.md` |
| VIS-01 | Дерево синтаксичного виводу: text, JSON, DOT, SVG | 1.5 | `src/sipl/visualization/` |
| SEM-01 | Семантичний терм програми в нотації курсу | 2.0 | `src/sipl/semantics/` |
| REL-01 | CI: lint + tests + збірка на кожен PR | 0.5 | `.github/workflows/ci.yml` |
| REL-02 | GitHub Release + SemVer + CHANGELOG | 0.5 | `.github/workflows/release.yml`, `CHANGELOG.md` |
| REL-03 | Публікація пакета в PyPI | 0.5 | `.github/workflows/release.yml` |
| **Разом основне** | | **10.0** | |
| CORE-04 | Подієва модель виконання і trace *(запас)* | 1.0 | `src/sipl/interpreter/core.py`, `sipl trace` |
| IDE-01 | VS Code: `.sipl`, підсвітка, коментарі, дужки, відступи, сніпети *(запас)* | 1.0 | `vscode-sipl/` |
| **Заявлено** | | **12.0** (зараховується не більше 10) | |

## Встановлення

Потрібен Python 3.10+.

```bash
pip install sipl-toolkit

git clone https://github.com/QuantGit43/sipl-toolkit && cd sipl-toolkit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Перевірка: `sipl --version` і `pytest`.

## Використання

```bash
sipl check examples/sum_geom3.sipl
sipl parse examples/power.sipl --json

sipl run examples/sum_geom3.sipl -s N=3
sipl trace examples/power.sipl -s X=5 -s Y=2
sipl run examples/errors/infinite_loop.sipl -s X=1 --max-steps 1000

sipl term examples/sum_geom3.sipl
sipl term examples/sum_geom3.sipl --chain
sipl term examples/power.sipl --steps
sipl term examples/power.sipl --format latex

sipl tree examples/power.sipl
sipl tree examples/power.sipl --format svg -o tree.svg
sipl tree examples/power.sipl --format dot | dot -Tpng -o tree.png
```

Будь-яка команда з `--json` повертає стабільний конверт (`schema_version: 1`), див.
[docs/json-format.md](docs/json-format.md). Коди завершення: `0` успіх, `1` синтаксична
помилка, `2` аргументи, `3` помилка виконання, `4` результат невизначений, `5` ввід/вивід.

Приклад помилки:

```
$ sipl check examples/errors/ge_operator.sipl
examples/errors/ge_operator.sipl:3:14: error[E002]: Неочікуваний фрагмент '='. Очікувалось: '(', змінна, число. Підказка: оператора '>=' немає в SIPL: використайте X > Y ∨ X = Y
```

### Як бібліотека

```python
from sipl.parser import parse
from sipl.interpreter import run
from sipl.semantics import semantic_term, to_text
from sipl.visualization import build_parse_tree, numbered_yield

prog = parse(open("examples/sum_geom3.sipl", encoding="utf-8").read())
print(run(prog, {"N": 3}).state)
print(to_text(semantic_term(prog)))
print(numbered_yield(build_parse_tree(prog)))
```

## Мова SIPL

```
begin
    R := 1;
    while Y > 0 do
    begin
        R := R * X;
        Y := Y - 1
    end
end
```

Оператори: `x := a`, `S1; S2`, `if b then S1 else S2`, `while b do S`, `begin S end`, `skip`.
Вирази: числа, змінні, `+ - *`, дужки. Умови: `=`, `>`, `∨` (або `or`), `¬` (або `not`), дужки.
Коментарі `// ...`. Повна граматика й пріоритети — [grammar/README.md](grammar/README.md).

## Приклади

| Файл | Що обчислює | Запуск |
|---|---|---|
| `examples/sum_geom3.sipl` | 1 + 3 + … + 3ⁿ (варіант 19) | `-s N=3` → `S = 40` |
| `examples/power.sipl` | xʸ (практикум, с. 9) | `-s X=5 -s Y=2` → `R = 25` |
| `examples/division.sipl` | x div y (практикум, с. 23) | `-s X=7 -s Y=4` → `R = 1` |
| `examples/gcd.sipl` | НСД (лекція 1-2) | `-s M=8 -s N=16` → `M = N = 8` |
| `examples/factorial.sipl` | n! | `-s N=5` → `F = 120` |
| `examples/abs_max.sipl` | max(\|x\|, \|y\|), розгалуження | `-s X=-7 -s Y=4` → `M = 7` |
| `examples/errors/*.sipl` | приклади помилок і нескінченного циклу | |

## VS Code

Каталог [`vscode-sipl/`](vscode-sipl/) — окремий клієнт без логіки мови (лише підсвітка).

```bash
cd vscode-sipl && npm ci && npm test && npx vsce package
code --install-extension sipl-language-0.1.0.vsix
```

## Архітектура і теорія

* [docs/architecture.md](docs/architecture.md) — шари, модулі, рішення.
* [docs/theory.md](docs/theory.md) — відповідність практичним роботам 1–3 та правилам курсу.
* [docs/json-format.md](docs/json-format.md) — JSON-контракт CLI.

## Розробка

```bash
ruff check .
pytest -q
python -m build
```

## Реліз

1. Оновити версію в `pyproject.toml`, `src/sipl/__init__.py`, `vscode-sipl/package.json` і додати розділ у `CHANGELOG.md`.
2. `git tag v0.1.0 && git push --tags` — workflow `release.yml` збере пакет і `.vsix`,
   створить GitHub Release з нотатками з CHANGELOG і опублікує пакет у PyPI.
3. Для PyPI один раз налаштувати Trusted Publisher на pypi.org: проєкт `sipl-toolkit`,
   репозиторій `QuantGit43/sipl-toolkit`, workflow `release.yml`, environment `pypi`.
   Якщо назва `sipl-toolkit` на PyPI зайнята, змінити `name` у `pyproject.toml`.

## Обмеження

* Нескінченні цикли виявляються лише лімітом кроків (`--max-steps`, типово 100 000): у загальному
  випадку завершуваність нерозв'язна.
* Операцій `div`, `mod`, `<`, `>=` у базовій SIPL немає — парсер підказує, як їх замінити.
* Доведення коректності (практична 3) не автоматизоване; `sipl trace` допомагає перевірити інваріант на даних.
* Підсвітка у VS Code — синтаксична (TextMate), без діагностики в редакторі.

## Ліцензія

MIT
