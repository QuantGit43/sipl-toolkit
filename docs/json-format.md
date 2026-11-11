# JSON-формат CLI (schema_version = 1)

Кожна команда з `--json` друкує один JSON-об'єкт:

```json
{
  "schema_version": 1,
  "tool": "sipl",
  "version": "0.1.0",
  "command": "run",
  "ok": true,
  "result": { ... },
  "diagnostics": [ ... ]
}
```

Поля конверта стабільні в межах `schema_version: 1`; нові поля в `result` можуть додаватися.

## Діагностика

```json
{ "code": "E002", "severity": "error", "message": "...", "line": 3, "column": 14,
  "end_line": 3, "end_column": 15 }
```

| Код | Значення |
|---|---|
| E001 | неочікуваний кінець програми |
| E002 | неочікуваний фрагмент (з підказкою для `>=`, `<`, `/`, …) |
| E003 | неочікуваний токен |
| E004 | порожня програма |
| R001 | змінна без значення в стані (`x⇒(st)` невизначене) |
| R002 | перевищено ліміт кроків (результат `↑`) |
| U001 | неправильний аргумент (напр. `-s X5`) |
| IO01 | не вдалося прочитати файл |
| W001 | обхід листків дерева не збігся з текстом (попередження) |

## `result` за командами

| Команда | `result` |
|---|---|
| `parse` | AST: `{"type": "Program", "body": {...}, "span": {...}}` |
| `check` | `{"valid": true, "normalized": "begin ... end"}` |
| `run` | `{"defined": bool, "initial_state": {}, "final_state": {}, "steps": int}` |
| `trace` | як `run` + `"events": [...]` |
| `term` | `{"term": str, "latex": str, "tree": {...}}` + `chain`/`steps` за прапорцями |
| `tree` | `{"tree": {...}, "yield": "1 begin 2 R ...", "yield_matches_source": bool}` |

## Події trace

| `event` | Поля |
|---|---|
| `before` | `node`, `text`, `span` |
| `assign` | `name`, `old` (null, якщо змінної не було), `new`, `span` |
| `condition` | `construct` (`if`/`while`), `text`, `value`, `span` |
| `after` | `node`, `span` |
| `finish` | `state` |

Кожна подія має `step` — номер кроку виконання.

## Коди завершення

`0` успіх · `1` синтаксична помилка · `2` аргументи · `3` помилка виконання · `4` результат невизначений (ліміт кроків) · `5` ввід/вивід
