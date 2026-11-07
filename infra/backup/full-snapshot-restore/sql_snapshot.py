"""Restricted mysqldump INSERT parser for private byte-for-byte row verification."""
import hashlib,re
class Unsupported(ValueError):pass

def statements(text):
 start=0;i=0;quote=None;line=False;block=False
 while i<len(text):
  c=text[i];n=text[i:i+2]
  if line:
   if c=='\n':line=False
  elif block:
   if n=='*/':block=False;i+=1
  elif quote:
   if c=='\\':i+=1
   elif c==quote:
    if i+1<len(text) and text[i+1]==quote:i+=1
    else:quote=None
  elif c in "'\"`":quote=c
  elif n=='/*':block=True;i+=1
  elif n=='--' and (i+2==len(text) or text[i+2].isspace()):line=True
  elif c=='#':line=True
  elif c==';':yield text[start:i+1];start=i+1
  i+=1
 if quote or block:raise Unsupported('unterminated SQL token')
 if re.sub(r'--[^\n]*|/\*.*?\*/','',text[start:],flags=re.S).strip():raise Unsupported('unterminated SQL statement')

def clean(statement):
 out=[];i=0;quote=None
 while i<len(statement):
  c=statement[i];n=statement[i:i+2]
  if quote:
   out.append(c)
   if c=='\\' and i+1<len(statement):i+=1;out.append(statement[i])
   elif c==quote:
    if i+1<len(statement) and statement[i+1]==quote:i+=1;out.append(statement[i])
    else:quote=None
  elif c in "'\"`":quote=c;out.append(c)
  elif n=='/*':
   end=statement.find('*/',i+2)
   if end<0:raise Unsupported('unterminated comment')
   i=end+1;out.append(' ')
  elif c=='#' or (n=='--' and (i+2==len(statement) or statement[i+2].isspace())):
   end=statement.find('\n',i)
   if end<0:break
   i=end;out.append('\n')
  else:out.append(c)
  i+=1
 return ''.join(out).strip()

def parse_values(text):
 rows=[];i=0;n=len(text);esc={'0':'\0','b':'\b','n':'\n','r':'\r','t':'\t','Z':'\x1a'}
 def space():
  nonlocal i
  while i<n and text[i].isspace():i+=1
 while True:
  space()
  if i>=n or text[i]!='(':raise Unsupported('expected INSERT tuple')
  i+=1;row=[]
  while True:
   space()
   if i<n and text[i]=="'":
    i+=1;value=[]
    while i<n:
     c=text[i];i+=1
     if c=='\\':
      if i>=n:raise Unsupported('truncated SQL string escape')
      e=text[i];i+=1;value.append(esc.get(e,e))
     elif c=="'":
      if i<n and text[i]=="'":value.append("'");i+=1
      else:break
     else:value.append(c)
    else:raise Unsupported('unterminated SQL value')
    value=''.join(value).encode('utf-8')
   else:
    start=i
    while i<n and text[i] not in ',)':i+=1
    token=text[start:i].strip()
    if token=='NULL':value=None
    elif re.fullmatch(r'-?(?:\d+)(?:\.\d+)?(?:[eE][+-]?\d+)?',token):value=token.encode()
    elif re.fullmatch(r'0x(?:[a-fA-F0-9]{2})*',token):value=bytes.fromhex(token[2:])
    else:raise Unsupported('unsupported SQL value expression')
   row.append(value);space()
   if i>=n:raise Unsupported('truncated SQL tuple')
   c=text[i];i+=1
   if c==')':break
   if c!=',':raise Unsupported('unexpected SQL tuple delimiter')
  rows.append(tuple(row));space()
  if i<n and text[i]==',':i+=1;continue
  if text[i:].strip()!=';':raise Unsupported('unexpected INSERT suffix')
  return rows

def row_digest(rows):
 hashes=[]
 for row in rows:
  h=hashlib.sha256()
  for value in row:
   if value is None:h.update(b'N;')
   else:h.update(b'B'+str(len(value)).encode()+b':'+value+b';')
  hashes.append(h.digest())
 return hashlib.sha256(b''.join(sorted(hashes))).hexdigest()

def parse(text):
 if re.search(r'\b(?:CREATE|ALTER)\s+(?:DEFINER\s*=.*?)?\b(?:PROCEDURE|FUNCTION|TRIGGER|EVENT)\b',text,re.I|re.S):raise Unsupported('unexpected executable schema object; review required')
 dbs=set(re.findall(r'CREATE DATABASE[^;]*?`([^`]+)`',text,re.I))|set(re.findall(r'\bUSE\s+`([^`]+)`',text,re.I))
 if dbs!={'nacos_prod'}:raise Unsupported('dump schema set must be exact nacos_prod')
 tables={};rows={}
 for raw in statements(text):
  stmt=clean(raw)
  if not stmt:continue
  if stmt.upper().startswith('CREATE TABLE'):
   m=re.match(r'CREATE TABLE `([a-zA-Z0-9_]+)`\s*\((.*)\)\s*ENGINE=',stmt,re.S)
   if not m:raise Unsupported('unsupported CREATE TABLE form')
   table=m[1];columns=re.findall(r'^\s*`([^`]+)`\s+',m[2],re.M)
   if not columns or table in tables or any(not re.fullmatch(r'[a-zA-Z0-9_]+',c) for c in columns):raise Unsupported('invalid/duplicate table definition')
   tables[table]=columns;rows[table]=[]
  elif stmt.upper().startswith(('INSERT ','REPLACE ')):
   m=re.match(r'INSERT INTO `([a-zA-Z0-9_]+)` VALUES\s*(.*)',stmt,re.S)
   if not m or m[1] not in tables:raise Unsupported('unsupported INSERT form/order')
   parsed=parse_values(m[2])
   if any(len(r)!=len(tables[m[1]]) for r in parsed):raise Unsupported('INSERT column count mismatch')
   rows[m[1]].extend(parsed)
 required={'config_info','users','roles','permissions'}
 if not required<=set(tables) or not rows['users']:raise Unsupported('required Nacos metadata/users missing')
 if not {'username','password','enabled'}<=set(tables['users']):raise Unsupported('unsupported users schema')
 return {name:{'columns':columns,'rows':len(rows[name]),'digest':row_digest(rows[name])} for name,columns in tables.items()}
