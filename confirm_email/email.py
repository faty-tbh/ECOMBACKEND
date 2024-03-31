# confirmation_email/email_functions.py
from email.message import EmailMessage
import ssl
import smtplib
import uuid
import datetime

def send_confirmation_email(author_email, first_name, order_number, items_quantity,total, adress):
    current_date = datetime.date.today()
    confirmation_code = str(uuid.uuid4())[:8].upper()
    confirmation_message = f"""
            Dear {first_name},

            Thank you for choosing Capital Book for your recent order! We're thrilled to confirm that your purchase has been successfully processed. Below, you'll find the details of your order:

            Order Number: {order_number}
            Date of Purchase: {current_date}

            Ordered Items: {items_quantity}

           

            Total Amount: {total}

            Adresse: {adress}

            We appreciate your support and hope you enjoy your new books. If you have any questions or concerns regarding your order, please don't hesitate to contact us at [Your Email Address]. Our customer service team is here to assist you.

            Thank you again for shopping with Capital Book. We look forward to serving you again soon.

            Best Regards,
            
            Capital Book Customer Service Team
            """

    msg = EmailMessage()
    msg.set_content(confirmation_message)
    msg["Subject"] = "Your Order Confirmation from Capital Book"
    msg["From"] = "publishour@gmail.com"  # Remplacez par votre adresse e-mail
    msg["To"] = author_email

    # Configuration du serveur SMTP (Gmail dans cet exemple)
    smtp_server = "smtp.gmail.com"
    smtp_port = 465
    smtp_username = "publishour@gmail.com"  # Remplacez par votre adresse e-mail Gmail
    smtp_password = "yoyi onqp eopn rcpu"  # Remplacez par votre mot de passe Gmail
    context = ssl.create_default_context()

    # Envoi de l'e-mail
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
        server.login(smtp_username, smtp_password)
        server.send_message(msg)

    return confirmation_code
