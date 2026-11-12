' Khoi dong lai app POLY Cut (sau khi cap nhat server.py): tat may chu cu, bat lai may chu moi.
' Video dang dung khong bi anh huong (claude.exe chay rieng). Cua so app dang mo tu tai lai; chua mo thi bam icon.
Option Explicit
Dim sh, fso, app, url, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
app = fso.GetParentFolderName(WScript.ScriptFullName)
url = "http://127.0.0.1:8790/"

Function Song()
  Dim h
  On Error Resume Next
  Set h = CreateObject("MSXML2.ServerXMLHTTP.6.0")
  h.setTimeouts 800, 800, 800, 800
  h.Open "GET", url & "api/ping", False
  h.Send
  Song = (Err.Number = 0)
  If Song Then Song = (h.Status = 200)
  Err.Clear
  On Error GoTo 0
End Function

Sub Tat()
  Dim h
  On Error Resume Next
  Set h = CreateObject("MSXML2.ServerXMLHTTP.6.0")
  h.setTimeouts 800, 800, 800, 800
  h.Open "POST", url & "api/tat", False
  h.setRequestHeader "Content-Type", "application/json"
  h.Send "{}"
  Err.Clear
  On Error GoTo 0
End Sub

If Song() Then
  Tat
  For i = 1 To 40
    WScript.Sleep 250
    If Not Song() Then Exit For
  Next
End If
sh.Run "wscript """ & app & "\POLY Cut.vbs"" chi-may-chu", 0, True
