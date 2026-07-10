' Hermes Agent v1 — Silent Launcher for Windows Taskbar
' Run without CMD window appearing
' Usage: wscript.exe "scripts\hermes_silent.vbs" health

Dim command, shell
Set shell = CreateObject("WScript.Shell")

If WScript.Arguments.Count > 0 Then
    command = WScript.Arguments(0)
Else
    command = "help"
End If

shell.Run "wsl -d Ubuntu -- cd ~/projects/Rastro && python run.py --hermes " & command, 0, False
