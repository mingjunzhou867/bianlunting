$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$EvalScript = Join-Path $ProjectRoot "tests\agents_test\multi_agent_eval.py"
$Samples = Join-Path $ProjectRoot "tests\agents_test\policy_eval_samples.json"

& $PythonExe $EvalScript `
  --samples $Samples `
  --difficulty complex `
  --persona-mode off
