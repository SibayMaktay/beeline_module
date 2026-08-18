import os
from dotenv import load_dotenv

dotenv_path = './config/.env'

load_dotenv(dotenv_path=dotenv_path)

beeline_login = os.getenv('BEELINE_LOGIN')
beeline_password = os.getenv('BEELINE_PASSWORD')
beeline_url_base = os.getenv('BEELINE_URL_BASE', "https://my.beeline.ru")
# Секретный ключ для hash статичного ключа REST (может отсутствовать в демо)
beeline_rest_signature = os.getenv('BEELINE_REST_SIGNATURE')

utm5_port = os.getenv('UTM5_PORT', "9080")
utm5_api_url = f"{os.getenv('UTM5_API_URL', 'http://localhost')}" # {utm5_port}
utm5_login = os.getenv('UTM5_LOGIN')
utm5_password = os.getenv('UTM5_PASSWORD')
utm5_api_key = os.getenv('UTM5_API_KEY')

module_host = "127.0.0.1"
module_port = "9090"
module_api_key = os.getenv('MODULE_API_KEY')

log_level = "INFO" # default = INFO
log_file = "/var/log/beeline_module/module.log" # default = /var/log/beeline_module/module.log
