import sys, i18n, mstarpaths, os, minestar, string

logger = minestar.initApp()


def isInternalEmailEnabled():
    return minestar.parseBoolean(mstarpaths.interpretVar("_EMAIL_ENABLED_INT"), "mstaremail")

def isExternalEmailEnabled():
    return minestar.parseBoolean(mstarpaths.interpretVar("_EMAIL_ENABLED_EXT"), "mstaremail")

def __buildHeaders(sender, receiver, subject):
    headers = { "From" : sender, "To" : receiver, "Subject" : subject }
    return headers

def __buildMessage(headers, body):
    lines = []
    for (key, value) in headers.items():
        lines.append("%s: %s" % (key, value))
    lines = lines + ["", body]
    return string.join(lines, "\n")

def __getSMTP():
    emailType = mstarpaths.interpretVar("_EMAILTYPE")
    if emailType != "SMTP":
        minestar.fatalError("mstaremail", i18n.translate("Email type %s is not supported") % emailType)
    fromAddress = mstarpaths.interpretVar("_EMAILSENDER")
    user = mstarpaths.interpretVar("_EMAILUSER")
    password = mstarpaths.interpretVar("_EMAILPASSWORD")
    port = mstarpaths.interpretVar("_EMAILPORT")
    import smtplib
    smtp = None
    try:
        smtp = smtplib.SMTP(mstarpaths.interpretVar("_EMAILSERVER"), port)
        if user is not None and password is not None and len(user) > 0:
           smtp.login(user, password)
    except smtplib.SMTPAuthenticationError, authEx:
        print i18n.translate("Login to SMTP mail server failed due to invalid user/passwd.  Processing continuing...")
        print i18n.translate("      Actual exception message was : %s") % authEx
    except smtplib.SMTPException, genEx:
        print i18n.translate("No suitable SMTP authentication method was found.  Processing continuing...")
        print i18n.translate("      Actual exception message was : %s") % genEx
    except:
        print i18n.translate("Login to SMTP mail server failed.  Processing continuing...")
    return (fromAddress, smtp)

def __attachFile(mesg, attachment, disposition):
    "Attach a file to a MIME Multipart message"
    if not os.access(attachment, os.F_OK):
        minestar.fatalError("mstaremail", i18n.translate("Attachment %s to be sent does not exist") % attachment)
    if not os.access(attachment, os.R_OK):
        minestar.fatalError("mstaremail", i18n.translate("Attachment %s to be sent is not readable") % attachment)
    import mimetypes
    from email import Encoders
    from email.Message import Message
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEAudio import MIMEAudio
    from email.MIMEBase import MIMEBase
    from email.MIMEImage import MIMEImage
    from email.MIMEText import MIMEText
    (ctype, encoding) = mimetypes.guess_type(attachment)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    (maintype, subtype) = ctype.split('/', 1)
    mf = open(attachment, "rb")
    content = mf.read()
    mf.close()
    if maintype == "text":
        subMesg = MIMEText(content, _subtype=subtype)
    elif maintype == "image":
        subMesg = MIMEImage(content, _subtype=subtype)
    elif maintype == "audio":
        subMesg = MIMEAudio(content, _subtype=subtype)
    else:
        subMesg = MIMEBase("application", "octet-stream")
        subMesg.set_payload(content)
        Encoders.encode_base64(subMesg)
    if disposition == "attachment":
        subMesg.add_header('Content-Disposition', disposition, filename=attachment)
    else:
        # must omit the filename, or else some Windows program displays
        # it as an attachment
        subMesg.add_header('Content-Disposition', disposition)
    mesg.attach(subMesg)

def resolveRecipient(to):
    if to.find("@") < 0:
        # using emailGroups.properties file
        import emailGroups
        group = emailGroups.getGroup(to)
        if group is not None:
            to = ", ".join(group)
            list = group
    else:
        # explicit addresses in supervisor
        if to.find(",") > -1:
            list = to.split(",")
        elif to.find(";") > -1:
            list = to.split(";")
        else:
            list = [to]
        # strip spaces
        for addrIndex in range(len(list)):
            list[addrIndex] = list[addrIndex].strip()              
    return (to, list)

def email(to, subject, messageFile=None, attachments=[]):
    mstarpaths.loadMineStarConfig()
    # figure out the recipients
    (to, toList) = resolveRecipient(to)
    # get an SMTP connection
    (sender, smtp) = __getSMTP()
    from email.MIMEMultipart import MIMEMultipart
    mesg = MIMEMultipart()
    for (key, value) in __buildHeaders(sender, to, subject).items():
        mesg[key] = value
    #mesg.preamble = "Constructed by mstaremail.py\n"
    #mesg.epilogue = ""
    # attach the message text
    if messageFile is not None:
        __attachFile(mesg, messageFile, "inline")
    # attach the attachments
    for attachment in attachments:
        __attachFile(mesg, attachment, "attachment")
    # mesg.add_payload("wassup?")
    # send it
    #smtp.set_debuglevel(1)
    smtp.sendmail(sender, toList, mesg.as_string())
    smtp.quit()

def quickEmail(to, subject, message):
    mstarpaths.loadMineStarConfig()
    (to, toList) = resolveRecipient(to)
    if not toList:
       print ("WARNING - No recipient to mail about completed FTP - %s" % subject)
       minestar.logit("WARNING - No recipient to mail about completed FTP - %s" % subject)
       return
    (sender, smtp) = __getSMTP()
    headers = __buildHeaders(sender, to, subject)
    smtp.sendmail(sender, toList, __buildMessage(headers, message))
    smtp.quit()

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 3:
        fileExists = os.access(args[1], os.F_OK)
        if fileExists:
            email(args[0], args[1], args[2])
        else:
            quickEmail(args[0], args[1], args[2])
    elif len(args) >= 2:
        email(args[0], args[1], args[2], args[3:])
    elif len(args) == 1 and args[0] == "TEST":
        subject = i18n.translate("This is a test message")
        message = i18n.translate("This is to see whether MineStar email is working")
        quickEmail("test_recipients", subject, message)
    else:
        print i18n.translate("You're not supposed to run this program!")
        print i18n.translate("Usage: mstaremail to subject messageFile [attachmentFile ...]")
        sys.exit(14)
