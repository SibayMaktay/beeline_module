import os
from dotenv import load_dotenv

dotenv_path = '.env'

load_dotenv(dotenv_path=dotenv_path)

beeline_login = os.getenv('BEELINE_LOGIN')
beeline_password = os.getenv('BEELINE_PASSWORD')
beeline_url_base = os.getenv('BEELINE_URL_BASE')

utm5_api_url = os.getenv('UTM5_API_URL')
utm5_login = os.getenv('UTM5_LOGIN')
utm5_password = os.getenv('UTM5_PASSWORD')

module_host = os.getenv('MODULE_HOST')
module_port = os.getenv('MODULE_PORT')
api_key = os.getenv('API_KEY')

log_level = "INFO" # default = INFO
log_file = "/var/log/beeline_module/module.log" # default = /var/log/beeline_module/module.log
