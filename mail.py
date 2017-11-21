# coding: utf-8
#!/usr/bin/python
import os
import sys
import time
import socket
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE,formatdate
from email import encoders
from email.header import Header


def send_mail(subject, content, to_list, files=None):
    msg = MIMEMultipart()
    fro = 'qdreamer_cloud@163.com'
    passwd = 'zhQdreamer2017'
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = fro
    msg['To'] = COMMASPACE.join(to_list)
    msg['Date'] = formatdate(localtime=True)
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    for f in files if files else []:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(open(f, 'rb').read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)

    try:
        s = smtplib.SMTP(timeout=3)
        s.connect('smtp.163.com')
        s.login(fro, passwd)
        s.sendmail(fro, to_list, msg.as_string())
        s.close()
        return True
    except Exception, e:
        import traceback
        traceback.print_exc()
        return False


def send_alert_mail(content):
    c = []
    c.append('Datetime: ' + time.asctime())
    c.append('Host: ' + socket.gethostname())
    c.append(content)
    to=[
        'all-monitor@qdreamer.com',
    ]
    send_mail('server monitor', '\n'.join(c), to)
