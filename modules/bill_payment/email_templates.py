"""
Email templates for bill payment notifications
"""

from typing import Optional
from datetime import datetime
from jinja2 import Template


class BillEmailTemplates:
    """Templates for sending bill-related emails to tenants"""
    
    @staticmethod
    def bill_created_template() -> Template:
        """Template for new bill creation notification"""
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Bill - {{ hostel_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px; }
        .bill-details { background: white; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #2563eb; }
        .amount { font-size: 24px; font-weight: bold; color: #2563eb; }
        .due-date { color: #dc2626; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 14px; }
        .payment-info { background: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; border: 1px solid #fbbf24; }
        .btn { display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏠 New Bill Generated</h1>
        <p>{{ hostel_name }}</p>
    </div>
    
    <div class="content">
        <p>Dear {{ tenant_name }},</p>
        
        <p>A new bill has been generated for your stay at {{ hostel_name }}. Please find the details below:</p>
        
        <div class="bill-details">
            <h3>Bill Details</h3>
            <p><strong>Bill Number:</strong> {{ bill_number }}</p>
            <p><strong>Description:</strong> {{ description or "Monthly Rent" }}</p>
            <p><strong>Amount:</strong> <span class="amount">₹{{ "%.2f"|format(amount) }}</span></p>
            <p><strong>Due Date:</strong> <span class="due-date">{{ due_date.strftime('%d %B %Y') }}</span></p>
            <p><strong>Generated on:</strong> {{ created_at.strftime('%d %B %Y') }}</p>
        </div>
        
        {% if payment_methods %}
        <div class="payment-info">
            <h4>💳 Payment Methods Available:</h4>
            <ul>
                {% for method in payment_methods %}
                <li>{{ method }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        
        <div style="text-align: center;">
            {% if payment_url %}
            <a href="{{ payment_url }}" class="btn">Pay Now</a>
            {% endif %}
            {% if bill_pdf_url %}
            <a href="{{ bill_pdf_url }}" class="btn" style="background: #64748b;">Download Bill PDF</a>
            {% endif %}
        </div>
        
        <p><strong>Please note:</strong></p>
        <ul>
            <li>Payment must be completed before the due date to avoid late fees</li>
            <li>If you have any questions, please contact the hostel management</li>
            <li>Keep this email for your records</li>
        </ul>
        
        <p>Thank you for your prompt payment!</p>
        
        <div class="footer">
            <p>Best regards,<br>Management Team<br>{{ hostel_name }}</p>
            <p style="font-size: 12px; margin-top: 20px;">
                This is an automated message. Please do not reply to this email.<br>
                For inquiries, contact: {{ hostel_email or 'support@hostelops.com' }}
            </p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)
    
    @staticmethod
    def payment_reminder_template() -> Template:
        """Template for payment reminder notification"""
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Reminder - {{ hostel_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f59e0b; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px; }
        .reminder-box { background: #fef3c7; padding: 20px; border-radius: 6px; margin: 20px 0; border: 2px solid #f59e0b; }
        .amount { font-size: 24px; font-weight: bold; color: #dc2626; }
        .due-date { color: #dc2626; font-weight: bold; }
        .urgent { color: #dc2626; font-weight: bold; text-transform: uppercase; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 14px; }
        .btn { display: inline-block; background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>⏰ Payment Reminder</h1>
        <p>{{ hostel_name }}</p>
    </div>
    
    <div class="content">
        <p>Dear {{ tenant_name }},</p>
        
        <div class="reminder-box">
            <h3 class="urgent">Action Required</h3>
            <p>This is a friendly reminder that your bill payment is due soon.</p>
            
            <h4>Bill Details:</h4>
            <p><strong>Bill Number:</strong> {{ bill_number }}</p>
            <p><strong>Amount Due:</strong> <span class="amount">₹{{ "%.2f"|format(amount) }}</span></p>
            <p><strong>Due Date:</strong> <span class="due-date">{{ due_date.strftime('%d %B %Y') }}</span></p>
            <p><strong>Days Remaining:</strong> {{ days_remaining }} days</p>
        </div>
        
        {% if days_remaining <= 3 %}
        <div style="background: #fee2e2; padding: 15px; border-radius: 6px; border: 1px solid #dc2626; margin: 20px 0;">
            <p><strong>⚠️ Urgent:</strong> Your payment is due very soon! Please pay immediately to avoid late fees.</p>
        </div>
        {% endif %}
        
        <div style="text-align: center;">
            {% if payment_url %}
            <a href="{{ payment_url }}" class="btn">Pay Now</a>
            {% endif %}
            {% if bill_pdf_url %}
            <a href="{{ bill_pdf_url }}" class="btn" style="background: #64748b;">View Bill</a>
            {% endif %}
        </div>
        
        <p>If you have already made the payment, please disregard this email. If you need assistance with payment or have any questions, please contact us immediately.</p>
        
        <div class="footer">
            <p>Best regards,<br>Management Team<br>{{ hostel_name }}</p>
            <p style="font-size: 12px; margin-top: 20px;">
                This is an automated reminder. Please do not reply to this email.<br>
                For inquiries, contact: {{ hostel_email or 'support@hostelops.com' }}
            </p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)
    
    @staticmethod
    def overdue_notice_template() -> Template:
        """Template for overdue payment notice"""
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Overdue Payment Notice - {{ hostel_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc2626; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px; }
        .overdue-box { background: #fee2e2; padding: 20px; border-radius: 6px; margin: 20px 0; border: 2px solid #dc2626; }
        .amount { font-size: 24px; font-weight: bold; color: #dc2626; }
        .late-fee { color: #dc2626; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 14px; }
        .btn { display: inline-block; background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 0; }
        .warning { background: #fef2f2; padding: 15px; border-radius: 6px; border-left: 4px solid #dc2626; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Overdue Payment Notice</h1>
        <p>{{ hostel_name }}</p>
    </div>
    
    <div class="content">
        <p>Dear {{ tenant_name }},</p>
        
        <div class="overdue-box">
            <h3>⚠️ Payment Overdue</h3>
            <p>Your payment was due on {{ due_date.strftime('%d %B %Y') }} and is now overdue by {{ days_overdue }} days.</p>
            
            <h4>Outstanding Amount:</h4>
            <p><strong>Original Amount:</strong> ₹{{ "%.2f"|format(original_amount) }}</p>
            {% if late_fee %}
            <p><strong>Late Fee:</strong> <span class="late-fee">₹{{ "%.2f"|format(late_fee) }}</span></p>
            {% endif %}
            <p><strong>Total Amount Due:</strong> <span class="amount">₹{{ "%.2f"|format(total_amount) }}</span></p>
            <p><strong>Bill Number:</strong> {{ bill_number }}</p>
        </div>
        
        <div class="warning">
            <p><strong>Important:</strong> Please settle this payment immediately to avoid additional late fees and potential service restrictions.</p>
        </div>
        
        <div style="text-align: center;">
            {% if payment_url %}
            <a href="{{ payment_url }}" class="btn">Pay Overdue Amount Now</a>
            {% endif %}
            {% if bill_pdf_url %}
            <a href="{{ bill_pdf_url }}" class="btn" style="background: #64748b;">View Bill Details</a>
            {% endif %}
        </div>
        
        <p>If you are experiencing difficulties with payment or believe this notice was sent in error, please contact the hostel management immediately to discuss payment arrangements.</p>
        
        <div class="footer">
            <p>Best regards,<br>Management Team<br>{{ hostel_name }}</p>
            <p style="font-size: 12px; margin-top: 20px;">
                This is an automated notice. Please do not reply to this email.<br>
                For inquiries, contact: {{ hostel_email or 'support@hostelops.com' }}<br>
                Phone: {{ hostel_phone or 'N/A' }}
            </p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)
    
    @staticmethod
    def payment_confirmation_template() -> Template:
        """Template for payment confirmation"""
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Confirmation - {{ hostel_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10b981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px; }
        .success-box { background: #d1fae5; padding: 20px; border-radius: 6px; margin: 20px 0; border: 2px solid #10b981; text-align: center; }
        .amount { font-size: 24px; font-weight: bold; color: #10b981; }
        .transaction-id { background: #f3f4f6; padding: 10px; border-radius: 4px; font-family: monospace; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 14px; }
        .btn { display: inline-block; background: #64748b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>✅ Payment Successful</h1>
        <p>{{ hostel_name }}</p>
    </div>
    
    <div class="content">
        <p>Dear {{ tenant_name }},</p>
        
        <div class="success-box">
            <h3>Thank You for Your Payment!</h3>
            <p>Your payment has been successfully processed.</p>
            
            <h4>Payment Details:</h4>
            <p><strong>Bill Number:</strong> {{ bill_number }}</p>
            <p><strong>Amount Paid:</strong> <span class="amount">₹{{ "%.2f"|format(amount) }}</span></p>
            <p><strong>Payment Date:</strong> {{ payment_date.strftime('%d %B %Y at %I:%M %p') }}</p>
            <p><strong>Payment Method:</strong> {{ payment_method }}</p>
            {% if transaction_id %}
            <p><strong>Transaction ID:</strong> <span class="transaction-id">{{ transaction_id }}</span></p>
            {% endif %}
        </div>
        
        <div style="text-align: center;">
            {% if receipt_url %}
            <a href="{{ receipt_url }}" class="btn">Download Receipt</a>
            {% endif %}
            {% if bill_pdf_url %}
            <a href="{{ bill_pdf_url }}" class="btn">View Paid Bill</a>
            {% endif %}
        </div>
        
        <p>Your payment has been recorded and your account is now up to date. Please keep this email for your records.</p>
        
        <p>If you have any questions about this payment or need additional documentation, please don't hesitate to contact us.</p>
        
        <div class="footer">
            <p>Best regards,<br>Management Team<br>{{ hostel_name }}</p>
            <p style="font-size: 12px; margin-top: 20px;">
                This is an automated confirmation. Please do not reply to this email.<br>
                For inquiries, contact: {{ hostel_email or 'support@hostelops.com' }}
            </p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)


def render_bill_email(template_type: str, context: dict) -> str:
    """
    Render a bill email template with the given context
    
    Args:
        template_type: Type of template ('created', 'reminder', 'overdue', 'confirmation')
        context: Dictionary containing template variables
    
    Returns:
        Rendered HTML email content
    """
    templates = BillEmailTemplates()
    
    template_map = {
        'created': templates.bill_created_template,
        'reminder': templates.payment_reminder_template,
        'overdue': templates.overdue_notice_template,
        'confirmation': templates.payment_confirmation_template
    }
    
    if template_type not in template_map:
        raise ValueError(f"Unknown template type: {template_type}")
    
    template = template_map[template_type]()
    return template.render(**context)
