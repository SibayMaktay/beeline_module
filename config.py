import os
from dotenv import load_dotenv

dotenv_path = '.env'

load_dotenv(dotenv_path=dotenv_path)

beeline_login = os.getenv('BEELINE_LOGIN')
beeline_password = os.getenv('BEELINE_PASSWORD')
beeline_url_base = "https://my.beeline.ru"

utm5_api_url = "http://localhost"
utm5_login = os.getenv('UTM5_LOGIN')
utm5_password = os.getenv('UTM5_PASSWORD')
utm5_port = "9080"

module_host = "127.0.0.1"
module_port = "9090"
api_key = os.getenv('API_KEY')

log_level = "INFO" # default = INFO
log_file = "/var/log/beeline_module/module.log" # default = /var/log/beeline_module/module.log
