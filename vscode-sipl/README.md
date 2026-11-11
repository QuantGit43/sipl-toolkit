# SIPL Language (VS Code)

Підсвітка синтаксису для мови SIPL з курсу «Теорія програмування» (IDE-01).

* файли `.sipl`;
* ключові слова `begin end if then else while do skip`, логічні `∨ ¬ or not`;
* змінні, числа, оператори `:= + - * = >`, коментарі `//`;
* пари дужок `begin/end`, `( )`, автовідступи, сніпети `program`, `while`, `if`, `begin`, `assign`.

Розширення не містить логіки мови: розбір і виконання — у пакеті `sipl-toolkit` (`sipl run file.sipl`).

## Встановлення з .vsix

```
code --install-extension sipl-language-0.1.0.vsix
```

Сумісність: VS Code 1.80+.
