; My Dear Cat — Windows installer (NSIS 3)
Unicode true
ManifestDPIAware true
!include "MUI2.nsh"

!define APPNAME  "My Dear Cat"
!define VERSION  "1.1.0"
!ifndef CONTENT
  !define CONTENT "..\staging"
!endif
!ifndef OUTFILE
  !define OUTFILE "..\out\MyDearCat-Setup.exe"
!endif
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Kedi"
!define RUNKEY  "Software\Microsoft\Windows\CurrentVersion\Run"
!define APPID   "com.hakan.kedi"

Name "${APPNAME}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\Kedi"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 64
BrandingText "My Dear Cat ${VERSION}"
ShowInstDetails nevershow
ShowUninstDetails nevershow

VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "My Dear Cat"
VIAddVersionKey /LANG=1033 "FileDescription" "My Dear Cat Setup"
VIAddVersionKey /LANG=1033 "CompanyName" "Hakan"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Hakan"
VIAddVersionKey /LANG=1033 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${VERSION}"

!define MUI_ICON   "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEFINISHPAGE_BITMAP "installer-sidebar.bmp"
!define MUI_WELCOMEPAGE_TITLE "Welcome to My Dear Cat"
!define MUI_WELCOMEPAGE_TEXT "This will install a little cat that lives on your desktop.$\r$\n$\r$\nIt sits in a corner of your screen. You can pet it, feed it, clean it and throw it a party.$\r$\n$\r$\nClick Next to continue."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TITLE "Your cat is ready!"
!define MUI_FINISHPAGE_TEXT "Your cat is waiting in the bottom-right corner of the screen.$\r$\n$\r$\nYou can drag it anywhere you like. For settings, right-click the cat icon next to the clock."
!define MUI_FINISHPAGE_RUN "$INSTDIR\Kedi.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Start the cat now"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Kedi"
  ; close a running cat first (including older versions)
  nsExec::Exec 'taskkill /IM Kedi.exe /F'
  Pop $0
  Sleep 700
  SetOutPath "$INSTDIR"
  File /r "${CONTENT}\*"
  WriteUninstaller "$INSTDIR\Kaldir.exe"

  ; shortcuts from the older Turkish version
  Delete "$DESKTOP\Kedi.lnk"
  Delete "$SMPROGRAMS\Kedi.lnk"
  Delete "$INSTDIR\BENIOKU.txt"
  CreateShortCut "$DESKTOP\My Dear Cat.lnk"    "$INSTDIR\Kedi.exe" "" "$INSTDIR\Kedi.exe" 0
  CreateShortCut "$SMPROGRAMS\My Dear Cat.lnk" "$INSTDIR\Kedi.exe" "" "$INSTDIR\Kedi.exe" 0

  WriteRegStr   HKCU "${UNINSTKEY}" "DisplayName"     "My Dear Cat"
  WriteRegStr   HKCU "${UNINSTKEY}" "DisplayIcon"     "$INSTDIR\Kedi.exe"
  WriteRegStr   HKCU "${UNINSTKEY}" "DisplayVersion"  "${VERSION}"
  WriteRegStr   HKCU "${UNINSTKEY}" "Publisher"       "Hakan"
  WriteRegStr   HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKCU "${UNINSTKEY}" "UninstallString" "$\"$INSTDIR\Kaldir.exe$\""
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "EstimatedSize" 560000
SectionEnd

Section "Uninstall"
  nsExec::Exec 'taskkill /IM Kedi.exe /F'
  Pop $0
  Sleep 700
  Delete "$DESKTOP\Kedi.lnk"
  Delete "$SMPROGRAMS\Kedi.lnk"
  Delete "$DESKTOP\My Dear Cat.lnk"
  Delete "$SMPROGRAMS\My Dear Cat.lnk"
  DeleteRegValue HKCU "${RUNKEY}" "${APPID}"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" "${APPID}"
  DeleteRegKey HKCU "${UNINSTKEY}"
  RMDir /r "$INSTDIR"
SectionEnd
