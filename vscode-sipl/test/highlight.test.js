const fs = require("fs");
const path = require("path");
const assert = require("assert");
const vsctm = require("vscode-textmate");
const oniguruma = require("vscode-oniguruma");

const wasm = fs.readFileSync(path.join(require.resolve("vscode-oniguruma"), "..", "onig.wasm")).buffer;
const onigLib = oniguruma.loadWASM(wasm).then(() => ({
  createOnigScanner: (p) => new oniguruma.OnigScanner(p),
  createOnigString: (s) => new oniguruma.OnigString(s),
}));

const registry = new vsctm.Registry({
  onigLib,
  loadGrammar: async () =>
    vsctm.parseRawGrammar(
      fs.readFileSync(path.join(__dirname, "..", "syntaxes", "sipl.tmLanguage.json"), "utf8"),
      "sipl.tmLanguage.json"
    ),
});

function scopesOf(grammar, line) {
  const { tokens } = grammar.tokenizeLine(line, vsctm.INITIAL);
  return tokens
    .map((t) => [line.slice(t.startIndex, t.endIndex), t.scopes[t.scopes.length - 1]])
    .filter(([text]) => text.trim() !== "");
}

(async () => {
  const g = await registry.loadGrammar("source.sipl");
  const cases = [
    ["while N > 0 do", [["while", "keyword.control.loop.sipl"], ["N", "variable.other.sipl"],
      [">", "keyword.operator.comparison.sipl"], ["0", "constant.numeric.integer.sipl"], ["do", "keyword.control.loop.sipl"]]],
    ["P := P * 3; // коментар", [["P", "variable.other.sipl"], [":=", "keyword.operator.assignment.sipl"],
      ["P", "variable.other.sipl"], ["*", "keyword.operator.arithmetic.sipl"], ["3", "constant.numeric.integer.sipl"],
      [";", "punctuation.terminator.statement.sipl"], ["// коментар", "comment.line.double-slash.sipl"]]],
    ["if ¬ M = N then skip else X2 := 1", [["if", "keyword.control.conditional.sipl"], ["¬", "keyword.operator.logical.sipl"],
      ["M", "variable.other.sipl"], ["=", "keyword.operator.comparison.sipl"], ["N", "variable.other.sipl"],
      ["then", "keyword.control.conditional.sipl"], ["skip", "keyword.other.skip.sipl"], ["else", "keyword.control.conditional.sipl"],
      ["X2", "variable.other.sipl"], [":=", "keyword.operator.assignment.sipl"], ["1", "constant.numeric.integer.sipl"]]],
  ];
  for (const [line, expected] of cases) {
    assert.deepStrictEqual(scopesOf(g, line), expected, line);
  }
  console.log(`OK: ${cases.length} рядки підсвічено правильно`);
})().catch((e) => { console.error(e); process.exit(1); });
