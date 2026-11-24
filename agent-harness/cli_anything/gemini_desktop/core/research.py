"""Select Gemini's Deep Research tool through Windows accessibility APIs."""

import json
import subprocess
from typing import Any, Dict


_SELECT_TOOL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]__HWND__)
if ($null -eq $root) { throw 'Gemini window is not accessible.' }
$scope = [System.Windows.Automation.TreeScope]::Descendants
$visible = [System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::IsOffscreenProperty, $false)

function Find-Control([string]$names, [bool]$buttonOnly = $false) {
    $elements = $root.FindAll($scope, $visible)
    foreach ($element in $elements) {
        if ($element.Current.IsEnabled -and $element.Current.Name -match $names) {
            $kind = $element.Current.ControlType
            if ($kind -eq [System.Windows.Automation.ControlType]::Button -or
                (-not $buttonOnly -and $kind -eq [System.Windows.Automation.ControlType]::MenuItem) -or
                (-not $buttonOnly -and $kind -eq [System.Windows.Automation.ControlType]::ListItem)) {
                return $element
            }
        }
    }
    return $null
}

function Invoke-Control($element) {
    $pattern = $null
    if ($element.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$pattern)) {
        $pattern.Select()
    } elseif ($element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
        $pattern.Invoke()
    } else {
        throw 'Gemini control does not expose an accessible select/invoke action.'
    }
}

$researchNames = '^(Deep Research|Pesquisa aprofundada|Investigação aprofundada)(\s|$)'
# A visible mode button means the tool is already selected; do not toggle it off.
$selected = Find-Control $researchNames $true
if ($null -ne $selected) {
    '{"success":true,"mode":"deep-research","already_selected":true}'
    exit 0
}
$tools = Find-Control '^(Tools|Ferramentas)(\s|$)' $true
if ($null -eq $tools) { throw 'Tools/Ferramentas button not found in Gemini accessibility tree.' }
Invoke-Control $tools
$deadline = [DateTime]::UtcNow.AddSeconds(5)
do {
    $tool = Find-Control $researchNames
    if ($null -ne $tool) { break }
    Start-Sleep -Milliseconds 200
} while ([DateTime]::UtcNow -lt $deadline)
if ($null -eq $tool) { throw 'Deep Research is unavailable in the Gemini tools menu.' }
Invoke-Control $tool
$deadline = [DateTime]::UtcNow.AddSeconds(5)
do {
    $selected = Find-Control $researchNames $true
    if ($null -ne $selected) {
        '{"success":true,"mode":"deep-research","already_selected":false}'
        exit 0
    }
    Start-Sleep -Milliseconds 200
} while ([DateTime]::UtcNow -lt $deadline)
throw 'Could not confirm that Deep Research was selected.'
"""


def select_deep_research(hwnd: int) -> Dict[str, Any]:
    """Fail closed if the native research mode cannot be selected and confirmed."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             _SELECT_TOOL_SCRIPT.replace("__HWND__", str(int(hwnd)))],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=15, creationflags=0x08000000,
        )
        if result.returncode:
            return {"success": False, "error": result.stderr.strip() or "Could not select Deep Research."}
        data = json.loads(result.stdout.strip())
        if not isinstance(data, dict) or data.get("success") is not True or data.get("mode") != "deep-research":
            return {"success": False, "error": "Gemini did not confirm Deep Research selection."}
        return data
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "error": f"Could not select Deep Research: {exc}"}
