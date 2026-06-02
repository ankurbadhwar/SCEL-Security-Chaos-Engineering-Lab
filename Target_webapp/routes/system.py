from flask import Blueprint, request, render_template
import os
import app.config as config

system_bp = Blueprint('system', __name__)


@system_bp.route('/ping', methods=['GET', 'POST'])
def ping():

    result = ""

    if request.method == 'POST':

        ip = request.form.get('ip')

        # =========================================
        # SECURE MODE
        # =========================================

        if config.INPUT_SANITIZATION_ENABLED:

            # Allow only digits and dots
            if not ip.replace('.', '').isdigit():

                return """
                <h2 style='color:red;text-align:center;margin-top:100px;'>
                Invalid IP Address
                </h2>
                """

            result = os.popen(f"ping -c 1 {ip}").read()

        # =========================================
        # VULNERABLE MODE
        # =========================================

        else:

            result = os.popen(f"ping -c 1 {ip}").read()

    return render_template(
        'ping.html',
        result=result
    )