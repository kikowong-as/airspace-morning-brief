"""（選用）警信。早報本身已改成網站，不再寄信；只有設定 SMTP 時才會寄警信。寄信（預設 Gmail SMTP + 應用程式密碼，免費）。環境變數：SMTP_USER SMTP_PASS MAIL_TO [MAIL_FROM SMTP_HOST SMTP_PORT]"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def configured():
    return bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS") and (os.environ.get("ALERT_TO") or os.environ.get("MAIL_TO")))


def send(subject, html_body, text_body="", to=None):
    to = to or os.environ["MAIL_TO"]
    recipients = [x.strip() for x in to.split(",") if x.strip()]
    user = os.environ["SMTP_USER"]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ.get("MAIL_FROM", user), ", ".join(recipients)
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "465"))) as s:
        s.login(user, os.environ["SMTP_PASS"])
        s.sendmail(user, recipients, msg.as_string())


def alert(subject, detail):
    """警信：寄給 ALERT_TO（沒設就寄給 MAIL_TO）。"""
    send(f"🚨 {subject}", f"<pre style='font-family:monospace;white-space:pre-wrap'>{detail}</pre>", detail,
         to=os.environ.get("ALERT_TO") or os.environ["MAIL_TO"])
