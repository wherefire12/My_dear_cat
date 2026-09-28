; My Dear Cat — Windows installer (NSIS 3)
; The wizard text is intentionally Turkish: the app was made for a Turkish user.
Unicode true
ManifestDPIAware true
!include "MUI2.nsh"

!define APPNAME  "Kedi"
!define VERSION  "1.0.1"
!ifndef CONTENT
  !define CONTENT "..\staging"
!endif
!ifndef OUTFILE
  !define OUTFILE "..\out\Kedi-Kurulum.exe"
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
BrandingText "Kedi ${VERSION}"
ShowInstDetails nevershow
ShowUninstDetails nevershow

VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1055 "ProductName" "Kedi"
VIAddVersionKey /LANG=1055 "FileDescription" "Kedi kurulumu"
VIAddVersionKey /LANG=1055 "CompanyName" "Hakan"
VIAddVersionKey /LANG=1055 "LegalCopyright" "Hakan"
VIAddVersionKey /LANG=1055 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1055 "ProductVersion" "${VERSION}"

!define MUI_ICON   "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEFINISHPAGE_BITMAP "installer-sidebar.bmp"
!define MUI_WELCOMEPAGE_TITLE "Kedi'ye hoş geldin"
!define MUI_WELCOMEPAGE_TEXT "Bu kurulum, masaüstünde yaşayan kediyi bilgisayarına yükleyecek.$\r$\n$\r$\nKedi ekranın köşesinde duracak; onu sevebilir, mama verebilir, temizleyebilir ve onunla parti yapabilirsin.$\r$\n$\r$\nDevam etmek için İleri'ye tıkla."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TITLE "Kedi hazır!"
!define MUI_FINISHPAGE_TEXT "Kedi ekranın sağ alt köşesinde seni bekliyor.$\r$\n$\r$\nOnu istediğin yere sürükleyebilirsin. Ayarlar için saatin yanındaki kedi simgesine sağ tıkla."
!define MUI_FINISHPAGE_RUN "$INSTDIR\Kedi.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Kediyi şimdi başlat"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Turkish"

Section "Kedi"
  ; close a running cat first (including older versions)
  nsExec::Exec 'taskkill /IM Kedi.exe /F'
  Pop $0
  Sleep 700
  SetOutPath "$INSTDIR"
  File /r "${CONTENT}\*"
  WriteUninstaller "$INSTDIR\Kaldir.exe"

  CreateShortCut "$DESKTOP\Kedi.lnk"     "$INSTDIR\Kedi.exe" "" "$INSTDIR\Kedi.exe" 0
  CreateShortCut "$SMPROGRAMS\Kedi.lnk"  "$INSTDIR\Kedi.exe" "" "$INSTDIR\Kedi.exe" 0

  WriteRegStr   HKCU "${UNINSTKEY}" "DisplayName"     "Kedi"
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
  DeleteRegValue HKCU "${RUNKEY}" "${APPID}"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" "${APPID}"
  DeleteRegKey HKCU "${UNINSTKEY}"
  RMDir /r "$INSTDIR"
SectionEnd
