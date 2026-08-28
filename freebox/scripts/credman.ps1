param(
  [Parameter(Mandatory=$true)][ValidateSet('get','set','delete')][string]$Action,
  [Parameter(Mandatory=$true)][string]$Target,
  [string]$UserName = 'freebox'
)

$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class CredMan {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct CREDENTIAL {
    public UInt32 Flags;
    public UInt32 Type;
    public string TargetName;
    public string Comment;
    public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
    public UInt32 CredentialBlobSize;
    public IntPtr CredentialBlob;
    public UInt32 Persist;
    public UInt32 AttributeCount;
    public IntPtr Attributes;
    public string TargetAlias;
    public string UserName;
  }

  [DllImport("advapi32.dll", EntryPoint="CredReadW", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern bool CredRead(string target, UInt32 type, UInt32 reservedFlag, out IntPtr credentialPtr);

  [DllImport("advapi32.dll", EntryPoint="CredWriteW", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern bool CredWrite(ref CREDENTIAL credential, UInt32 flags);

  [DllImport("advapi32.dll", EntryPoint="CredDeleteW", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern bool CredDelete(string target, UInt32 type, UInt32 flags);

  [DllImport("advapi32.dll", SetLastError=true)]
  public static extern void CredFree(IntPtr buffer);
}
"@

$CRED_TYPE_GENERIC = 1
# SESSION works reliably from non-interactive agent shells; credentials stay
# available for this Windows logon session without writing secrets to files.
$CRED_PERSIST_SESSION = 1

switch ($Action) {
  'get' {
    $ptr = [IntPtr]::Zero
    if (-not [CredMan]::CredRead($Target, $CRED_TYPE_GENERIC, 0, [ref]$ptr)) {
      exit 1
    }
    try {
      $cred = [Runtime.InteropServices.Marshal]::PtrToStructure($ptr, [type][CredMan+CREDENTIAL])
      if ($cred.CredentialBlobSize -gt 0) {
        [Console]::Out.Write([Runtime.InteropServices.Marshal]::PtrToStringUni($cred.CredentialBlob, [int]($cred.CredentialBlobSize / 2)))
      }
    } finally {
      [CredMan]::CredFree($ptr)
    }
  }
  'set' {
    $secret = [Console]::In.ReadToEnd()
    $blob = [Runtime.InteropServices.Marshal]::StringToCoTaskMemUni($secret)
    try {
      $cred = New-Object CredMan+CREDENTIAL
      $cred.Flags = 0
      $cred.Type = $CRED_TYPE_GENERIC
      $cred.TargetName = $Target
      $cred.CredentialBlobSize = [Text.Encoding]::Unicode.GetByteCount($secret)
      $cred.CredentialBlob = $blob
      $cred.Persist = $CRED_PERSIST_SESSION
      $cred.AttributeCount = 0
      $cred.Attributes = [IntPtr]::Zero
      $cred.TargetAlias = $null
      $cred.UserName = $UserName
      if (-not [CredMan]::CredWrite([ref]$cred, 0)) {
        throw ([ComponentModel.Win32Exception][Runtime.InteropServices.Marshal]::GetLastWin32Error())
      }
    } finally {
      if ($blob -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeCoTaskMemUnicode($blob) }
    }
  }
  'delete' {
    [void][CredMan]::CredDelete($Target, $CRED_TYPE_GENERIC, 0)
  }
}
