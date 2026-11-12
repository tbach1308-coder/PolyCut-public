' Tao icon "POLY Cut" ngoai Desktop (bam dup 1 lan). Icon mo app bang file POLY Cut.vbs canh day.
' 3/11: app doi ten POLY Team -> POLY Cut. Co icon cu "POLY Team" thi DOI TEN icon do (khong xoa), roi cap nhat cho mo POLY Cut.vbs.
Option Explicit
Dim sh, fso, app, lnk, desk, ten
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
app = fso.GetParentFolderName(WScript.ScriptFullName)
desk = sh.SpecialFolders("Desktop")
ten = "POLY Cut"   ' ten khong dau: WshShortcut.Save khong luu duoc ten co dau (loi 8007007B)
If fso.FileExists(desk & "\POLY Team.lnk") And Not fso.FileExists(desk & "\" & ten & ".lnk") Then fso.MoveFile desk & "\POLY Team.lnk", desk & "\" & ten & ".lnk"
Set lnk = sh.CreateShortcut(desk & "\" & ten & ".lnk")
lnk.TargetPath = sh.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\wscript.exe"
lnk.Arguments = """" & app & "\POLY Cut.vbs"""
lnk.WorkingDirectory = app
lnk.IconLocation = app & "\poly-team.ico,0"
lnk.Description = "POLY Cut - dung va sua video TikTok"
lnk.Save
' bao 4 giay roi tu dong (khong can bam OK)
If WScript.Arguments.Count = 0 Then sh.Popup "Da tao icon " & ten & " ngoai Desktop.", 4, "POLY Cut", 64
