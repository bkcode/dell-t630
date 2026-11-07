<?php
// Local root-only OMV management. Passwords arrive through stdin, never argv.
require_once('openmediavault/autoloader.inc');
require_once('openmediavault/globals.inc');
require_once('openmediavault/functions.inc');
if (posix_geteuid() !== 0 || gethostname() !== 'nas-media') {
    fwrite(STDERR, "NAS guest root only\n"); exit(2);
}
function safeResult($value, $key = '') {
    if (is_string($value) && preg_match('/^(password|passwd|secret|token|accessToken|sessionid|sessionId)$/i', $key)) return '[redacted]';
    if (is_array($value)) {
        $out = [];
        foreach ($value as $k => $v) $out[$k] = safeResult($v, (string)$k);
        return $out;
    }
    return $value;
}
try {
    $request = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
    $allowed = [
        'FileSystemMgmt' => ['enumerateFilesystems','enumerateMountedFilesystems','getList','getCandidates','getMountCandidates','create','setMountPoint','getDetails'],
        'ShareMgmt' => ['getCandidates','enumerateSharedFolders','getList','get','set','getPrivileges','setPrivileges','getPath'],
        'SMB' => ['getSettings','setSettings','getShareList','getShare','setShare'],
        'UserMgmt' => ['enumerateUsers','getUserList','getUser','setUser','getGroupList','getGroup','setGroup'],
        'FsTab' => ['set'],
        'Network' => ['setEthernetIface'],
        'SSH' => ['get','set','getStats'],
        'Exec' => ['isRunning','getOutput','getOutputAndStatus']
    ];
    $service = $request['service']; $method = $request['method'];
    if (!isset($allowed[$service]) || !in_array($method, $allowed[$service], true)) throw new RuntimeException('Method not allowlisted');
    $params = $request['params'] ?? null;
    $result = \OMV\Rpc\Rpc::call($service, $method, $params,
        ['username'=>'admin', 'role'=>OMV_ROLE_ADMINISTRATOR], \OMV\Rpc\Rpc::MODE_REMOTE);
    echo json_encode(['status'=>'ok', 'response'=>safeResult($result)], JSON_UNESCAPED_SLASHES), "\n";
} catch (Throwable $error) {
    $message = $error->getMessage();
    $redact = function($value, $key = '') use (&$redact, &$message) {
        if (is_array($value)) { foreach ($value as $k=>$v) $redact($v, (string)$k); }
        elseif (is_string($value) && strlen($value)>0 && preg_match('/password|passwd|secret|token/i', $key)) $message = str_replace($value, '[redacted]', $message);
    };
    $redact($request ?? []);
    echo json_encode(['status'=>'failed', 'error_type'=>get_class($error), 'message'=>$message]), "\n";
    exit(1);
}
