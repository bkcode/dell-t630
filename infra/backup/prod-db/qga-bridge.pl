#!/usr/bin/perl
# Fixed VM200 worker control and bounded file transport. No payload on stdout.
use strict;use warnings;use Fcntl qw(O_WRONLY O_CREAT O_EXCL O_NOFOLLOW);use MIME::Base64 qw(decode_base64 encode_base64);use JSON;use PVE::QemuServer::Agent qw(agent_cmd check_agent_error);use PVE::QemuServer::Monitor qw(mon_cmd);
my($op,$id,$name)=@ARGV;die "fixed run required\n"unless $>==0 && defined($id)&&$id=~/^[a-f0-9]{32}$/&&$op=~/^(export|pull|cleanup)$/;
my $VM=200;my $base='/mnt/pve/store/dell-artifacts/prod-db-backups';my $guest='/srv/dell-data/_prod_db_backups';alarm 1950;
if($op eq 'pull'){
 die "fixed file required\n"unless defined($name)&&($name eq 'manifest.json'||$name eq 'mysql.sql.gz');
 my $dest="$base/.partial-$id/$name";my $parent="$base/.partial-$id";my @st=lstat($parent);die "private staging required\n"unless @st&&-d _&&!(-l $parent)&&$st[4]==0&&($st[2]&0777)==0700;
 sysopen(my $f,$dest,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600)or die "private destination open failed\n";binmode($f);
 my $handle;my $total=0;my $max=$name eq 'manifest.json'?65536:1073741824;my $error;my $deadline=time()+1800;local $SIG{ALRM}=sub{die "bounded RPC timeout\n"};
 eval{
  alarm 20;$handle=agent_cmd($VM,'file-open',{path=>"$guest/$id/$name",mode=>'r'});
  while(1){
   die "transfer deadline\n" if time()>$deadline;alarm 20;my $r=mon_cmd($VM,'guest-file-read',handle=>$handle,count=>1048576);check_agent_error($r,'fixed read failed');
   die "bad count\n"unless defined($r->{count})&&$r->{count}=~/^\d+$/&&$r->{count}<=1048576;
   my $b=$r->{'buf-b64'}//'';die "bad encoding\n"unless length($b)<=1398104&&$b=~/^[A-Za-z0-9+\/]*={0,2}$/;
   my $raw=decode_base64($b);die "bad payload size\n"unless length($raw)==$r->{count}&&encode_base64($raw,'')eq $b;
   $total+=length($raw);die "bounded transfer exceeded\n"if $total>$max;
   print $f $raw or die "private write failed\n";
   last if $r->{eof};die "zero nonEOF read\n"unless $r->{count}>0;
  }
 };$error=$@;
 if(defined $handle){eval{alarm 20;my $r=mon_cmd($VM,'guest-file-close',handle=>$handle);check_agent_error($r,'close failed');};$error||=$@;}
 alarm 0;close($f)or $error||="destination close failed\n";die "bounded QGA transfer failed; partial retained\n"if $error;
 print encode_json({status=>'fixed-artifact-transferred',bytes=>$total,payload_printed=>JSON::false});
}else{
 my $cmd=['/usr/bin/python3','-I','-B','/usr/local/libexec/dell-prod-db-backup/guest-worker.py',$op,'--run-id',$id];
 my $started=PVE::QemuServer::Agent::qemu_exec($VM,undef,$cmd);die "fixed worker start failed\n"unless $started->{pid};my $end=time()+1900;
 while(time()<$end){my $r=PVE::QemuServer::Agent::qemu_exec_status($VM,$started->{pid});if($r->{exited}){die "fixed worker failed; private details withheld\n"unless defined($r->{exitcode})&&$r->{exitcode}==0;print encode_json({status=>'fixed-guest-worker-completed',operation=>$op,exitcode=>0});exit 0;}sleep 1;}
 die "fixed worker deadline; guest own deadline still enforced\n";
}
