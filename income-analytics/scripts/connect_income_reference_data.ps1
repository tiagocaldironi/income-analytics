param(
  [Parameter(Mandatory=$true)][string]$ReferenceDataRoot,
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'
$incomeSource = (Resolve-Path -LiteralPath $ReferenceDataRoot).Path
$incomeProject = (Resolve-Path -LiteralPath $ProjectRoot).Path
$incomeDestination = Join-Path $incomeProject 'data'
foreach ($incomeReferenceFile in @('magic_formula/canonical_rankings.db','magic_formula/universe_snapshots.db')) {
  if (!(Test-Path -LiteralPath (Join-Path $incomeSource $incomeReferenceFile) -PathType Leaf)) { throw "Missing published reference file: $incomeReferenceFile" }
}
if (Test-Path -LiteralPath $incomeDestination) {
  $incomeExisting = Get-Item -LiteralPath $incomeDestination
  if ($incomeExisting.LinkType -ne 'Junction' -or [System.IO.Path]::GetFullPath([string]$incomeExisting.Target).TrimEnd('\') -ne $incomeSource.TrimEnd('\')) {
    throw 'The project already has a different data directory. Nothing was replaced.'
  }
} else {
  New-Item -ItemType Junction -Path $incomeDestination -Target $incomeSource | Out-Null
}
Write-Output 'Published reference data connected. No snapshots were recalculated or published.'
