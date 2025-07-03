from pydantic import EmailStr
from sqlalchemy.orm import Session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import smtplib
import string
from app.config import settings
from fastapi import HTTPException, status

from app.models.models  import Staff, User
from app.utils.utils_schemas import EmailSendRequest


def send_reset_password_otp_to_email(email_data: EmailSendRequest, db: Session):
    # Fetch the user by email
    user = db.query(Staff).filter(Staff.email == email_data.email).first()
    
    if user:
        sender_email = "smartcode265@gmail.com"
        
        # Set content for password reset or account verification

        subject = "Password Reset Request: Timesheet and Leave Management LiHESS"
        body = f"""
        <html>
        <body>
            <h2>Dear {user.first_name} {user.last_name},</h2>
            <p>We received a request to reset your password. Use the OTP below to reset your password:</p>
            <p style="background-color: lightgrey; text-align: center; font-weight: bold; font-size: 20px;">{email_data.otp}</p>
            <p>If you did not request a password reset, please ignore this email.<br></p>
            <p style="color: red;">Please DO NOT forward this email or OTP to other staff members.</p>
            <p>Best regards,<br>LiHESS Team</p>
        </body>
        </html>
        """
        # Set up the email details
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = email_data.email
        msg["Reply-To"] = "notifications-no-reply@lighthouse.org.mw"

        # Attach the HTML body to the email
        msg.attach(MIMEText(body, "html"))

        # Send email using SMTP
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, settings.GMAIL_PASSWORD)
                server.sendmail(sender_email, email_data.email, msg.as_string())
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP email")

        return {"detail": f"OTP sent to {user.first_name} {user.last_name} successfully"}
    
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
   
   
def send_otp_to_email(email_data: EmailSendRequest, db: Session):
    # Fetch the user by email
    user = db.query(Staff).filter(Staff.email == email_data.email).first()
   
    if user:
        # Determine the subject and email body based on the user's role
        sender_email = "smartcode265@gmail.com"
        
        # Set the email content
        subject = "Activate Your Timesheet and Leave Management LiHESS Account"
        body = f"""
        <html>
        <body>
            <h2>Dear {user.first_name.title()} {user.last_name.title()}!</h2>
            <p>Your account has been created by the Timesheet and Leave Management Lighthouse Employee Self Service (LiHESS) system. <br>Your username is: <b>username:</b> <span style="color: blue; font-weight: bold;">{email_data.username}</span>. Use this activation code to activate:</p>
            <p style="background-color: lightgrey; text-align: center; font-weight: bold; font-size: 20px;">{email_data.otp}</p>
            <p>Please click the following link to activate your account: 
            <a href="#" target="_blank">https://lihess.lighthouse.org.mw</a></p>
            <p style="color: red;">DO NOT use your activation code as your password. <br>Please DO NOT forward this email to other staff members.</p>
            <p>If you have any questions or need assistance, feel free to reach out to the IT support team on <a href="mailto:itsupport@lighthouse.org.mw">itsupport@lighthouse.org.mw</a>.<br></p>
            <p>Best regards,<br>LiHESS Team</p>
        </body>
        </html>
        """

        # Set up the email details
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = email_data.email
        msg["Reply-To"] = "notifications-no-reply@lighthouse.org.mw"
        # Attach the HTML body to the email
        msg.attach(MIMEText(body, "html"))

        # Send email using SMTP
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, settings.GMAIL_PASSWORD)
                server.sendmail(sender_email, email_data.email, msg.as_string())
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP email")

        return {"detail": f"OTP sent to {user.first_name} {user.last_name} successfully"}
    
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


def send_account_verified_email(email: str, fullname: str):
    sender_email = "smartcode265@gmail.com"
    subject = "Account Activated Successfully: Your Timesheet and Leave Management LiHESS"
    html_message = f"""
    <html>
        <body>
            <h2>Hi {fullname},</h2>
            <p>Your account has been <strong>successfully activated</strong>. You can now log in using your new password.</p>
            <p>Please remember to keep your password safe and secure. If you forget your password, you can reset it using the 'Forgot Password' button on the login page.</p>
            <p>Click the following link to log in: 
            <a href="#" target="_blank">https://lihess.lighthouse.org.mw/login</a></p>
            <br>
            <p>Best regards,<br>The IT support</p>
        </body>
    </html>
    """
    # Set up email details
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = email
    msg["Reply-To"] = "notifications-no-reply@lighthouse.org.mw"
    msg.attach(MIMEText(html_message, "html"))

    # Send email using SMTP 
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, settings.GMAIL_PASSWORD)
            server.sendmail(sender_email, email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send notification email")

    return {"detail": f"Notification sent to {fullname} successfully"}


def send_transfer_notification_email(staff_email:EmailStr, full_name:str, old_coe_name:str, new_coe_name:str, new_username:str, center_name:str):
    """
    Sends an email to the staff member notifying them of their transfer and updated username.
    """
    sender_email = "smartcode265@gmail.com"
    subject = "Notification of Transfer and Updated Username"
    
    body = f"""
    <html>
    <body>
        <h2>Dear {full_name},</h2>
        <p>
            We are writing to inform you that you have been transferred from <strong>{old_coe_name}</strong> to 
            <strong>{new_coe_name}</strong>. This transfer is effective immediately, and all necessary updates 
            have been made in the system.
        </p>
        <p>
            As part of this transition, your username has been updated to reflect your new assignment. 
            Your updated username is:
        </p>
        <p style="background-color: lightgrey; text-align: center; font-weight: bold; font-size: 20px;">
            {new_username}
        </p>
        <p>
            Please use this updated username for all system-related activities moving forward. Your password 
            remains unchanged. If you experience any issues accessing your account, feel free to reach out 
            to the IT support team at <a href="mailto:itsupport@lighthouse.org.mw">itsupport@lighthouse.org.mw</a>.
        </p>
        <p>
            Thank you for your continued commitment and service. We wish you success at <strong>{new_coe_name}, {center_name}</strong>.
        </p>
        <p>Best regards,<br>LiHESS Team</p>
    </body>
    </html>
    """

    # Set up the email message
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = staff_email
    msg["Reply-To"] = "notifications-no-reply@lighthouse.org.mw"
    
    # Attach the HTML body to the email
    msg.attach(MIMEText(body, "html"))

    # Sending the email (SMTP logic should be added here)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, settings.GMAIL_PASSWORD)
            server.sendmail(sender_email, staff_email, msg.as_string())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to send transfer notification email: {str(e)}"
        )