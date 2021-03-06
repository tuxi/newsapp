# coding:utf8
from smtplib import SMTP_SSL
from email.header import Header
from email.mime.text import MIMEText
import os


EMAIL_HOST = 'smtp.exmail.qq.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'xy@swift.top' #os.environ.get('DJANGO_EMAIL_USER')
passwordfile = "emailpassword.txt"
if not os.path.exists(passwordfile):
    # 调用系统命令行来创建文件
    os.system(r"touch {}".format(passwordfile))
with open(passwordfile, 'r+') as pf:
    EMAIL_HOST_PASSWORD = pf.readline()

EMAIL_TO = ["wangshuai@swift.top", "coderhong@126.com"]
EMAIL_CC = ["sey@live.cn"]
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER


mail_info = {
    "from": EMAIL_HOST_USER,
    "to": ','.join(EMAIL_TO),
     "Cc": ','.join(EMAIL_CC),
    "hostname": EMAIL_HOST,
    "username": EMAIL_HOST_USER,
    "password": EMAIL_HOST_PASSWORD,
    "mail_subject": "News watch by swift.top",
    "mail_encoding": "utf-8"
}

def sendEmail(text):
    try:
        # 这里使用SMTP_SSL就是默认使用465端口
        smtp = SMTP_SSL(mail_info["hostname"])
        smtp.set_debuglevel(1)

        smtp.ehlo(mail_info["hostname"])
        smtp.login(mail_info["username"], mail_info["password"])

        msg = MIMEText(text, "plain", mail_info["mail_encoding"])
        msg["Subject"] = Header(mail_info["mail_subject"], mail_info["mail_encoding"])
        msg["from"] = mail_info["from"]
        msg["to"] = mail_info["to"]
        msg["Cc"] = mail_info["Cc"]

        smtp.sendmail(mail_info["from"], EMAIL_TO+EMAIL_CC, msg.as_string())

        smtp.quit()
    except Exception as e:
        print(e.__str__())
