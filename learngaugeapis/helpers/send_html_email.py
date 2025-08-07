import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import get_template

def send_html_template_email(to, subject, template_name, context):
    try:
        logging.info("send_html_template_email to=%s, subject=%s, template_name=%s, context=%s", to, subject, template_name, context)
        template = get_template(template_name)
        content = template.render(context=context)

        return send_mail(
            subject=subject,
            message="",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=to,
            html_message=content,
            auth_user=settings.EMAIL_HOST_USER,
            auth_password=settings.EMAIL_HOST_PASSWORD
        )
    except Exception as e:
        logging.exception("send_html_template_email exc=%s, to=%s, subject=%s, template_name=%s, context=%s", e, to, subject, template_name, context)
        raise e