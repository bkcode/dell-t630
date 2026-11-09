#!/usr/bin/perl
# Fixed VM210 isolated drill control and private PVE<->guest artifact transport.
use strict;use warnings;use Fcntl qw(O_RDONLY O_WRONLY O_CREAT O_EXCL O_NOFOLLOW);use MIME::Base64 qw(decode_base64 encode_base64);use JSON;use PVE::QemuServer::Agent qw(agent_cmd check_agent_error);use PVE::QemuServer::Monitor qw(mon_cmd);
my($op,$run,$source)=@ARGV;die "fixed restore run required\n"unless $>==0&&defined($run)&&$run=~/^[a-f0-9]{32}$/&&$op=~/^(prepare|restore|cleanup|write-archive|write-expected|read-report)$/;
my $vm=210;my $guest='/srv/dell-data/_prod_db_restore_drill';my $state='/var/lib/dell-prod-db-restore';my $backup='/mnt/pve/store/dell-artifacts/prod-db-backups';
my $h;my $error;local $SIG{ALRM}=sub{die "bounded RPC timeout\n"};
sub call {alarm 20;my($name,%arg)=@_;my $r=mon_cmd($vm,$name,%arg);check_agent_error($r,'fixed QGA operation');alarm 0;return $r;}
if($op=~/^write-/){
 my($name,$file,$max);if($op eq 'write-archive'){die "fixed backup source required\n"unless defined($source)&&$source=~/^[a-f0-9]{32}$/;($name,$file,$max)=('mysql.sql.gz',"$backup/$source/mysql.sql.gz",1073741824);}else{($name,$file,$max)=('expected.json',"$state/$run/expected.json",65536);}
 my @s=lstat($file);die "private regular source required\n"unless @s&&-f _&&!(-l $file)&&$s[4]==0&&($s[2]&0777)==0600&&$s[3]==1&&$s[7]>0&&$s[7]<=$max;
 sysopen(my $in,$file,O_RDONLY|O_NOFOLLOW)or die "source open failed\n";binmode($in);my $total=0;my $end=time()+900;
 eval{
  alarm 20;$h=agent_cmd($vm,'file-open',{path=>"$guest/$run/$name",mode=>'r+b'});alarm 0;
  while(1){die "transfer deadline\n"if time()>$end;my $count=sysread($in,my $buf,1048576);die "source read failed\n"unless defined $count;last unless $count;my $pos=0;my $writes=0;
   while($pos<$count){die "too many short writes\n"if ++$writes>16;my $part=substr($buf,$pos);my $r=call('guest-file-write',handle=>$h,'buf-b64'=>encode_base64($part,''));die "invalid write count\n"unless defined($r->{count})&&$r->{count}=~/^\d+$/&&$r->{count}>0&&$r->{count}<=length($part);$pos+=$r->{count};}
   $total+=$count;die "transfer cap\n"if $total>$max;
  }
  die "source length drift\n"unless $total==$s[7];call('guest-file-flush',handle=>$h);
 };$error=$@;
 if(defined $h){eval{call('guest-file-close',handle=>$h);};$error||=$@;}close $in;die "private restore transfer failed\n"if $error;
 print encode_json({status=>'fixed-private-file-written',bytes=>$total,payload_printed=>JSON::false});
}elsif($op eq 'read-report'){
 my $raw='';my $end=time()+60;eval{alarm 20;$h=agent_cmd($vm,'file-open',{path=>"$guest/reports/$run.json",mode=>'r'});alarm 0;
  while(1){die "report deadline\n"if time()>$end;my $r=call('guest-file-read',handle=>$h,count=>65536);my $b=$r->{'buf-b64'}//'';die "bad report encoding\n"unless $b=~/^[A-Za-z0-9+\/]*={0,2}$/;my $part=decode_base64($b);die "bad report count\n"unless defined($r->{count})&&length($part)==$r->{count}&&encode_base64($part,'')eq $b;$raw.=$part;die "report size\n"if length($raw)>65536;last if $r->{eof};die "zero nonEOF report\n"unless $r->{count}>0;}
 };$error=$@;if(defined $h){eval{call('guest-file-close',handle=>$h);};$error||=$@;}die "private report transfer failed\n"if $error;
 my $obj=decode_json($raw);die "fixed report identity\n"unless ref($obj)eq'HASH'&&$obj->{run_id}eq$run;
 my $file="$state/$run/guest-report.json";sysopen(my $out,$file,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600)or die "private report destination\n";print $out $raw;close $out;print encode_json({status=>'sanitized-report-stored-PVE',payload_printed=>JSON::false});
}else{
 alarm 1000;my $cmd=['/usr/bin/python3','-I','-B','/usr/local/libexec/dell-prod-db-restore/target-worker.py',$op,'--run-id',$run];my $r=PVE::QemuServer::Agent::qemu_exec($vm,undef,$cmd);die "fixed restore worker start\n"unless $r->{pid};my $end=time()+900;
 while(time()<$end){my $x=PVE::QemuServer::Agent::qemu_exec_status($vm,$r->{pid});if($x->{exited}){die "fixed restore worker failed; private report retained\n"unless defined($x->{exitcode})&&$x->{exitcode}==0;print encode_json({status=>'fixed-restore-worker-completed',operation=>$op,exitcode=>0});exit 0;}sleep 1;}die "restore worker deadline; cleanup required\n";
}
