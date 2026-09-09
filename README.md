# Модуль интеграции с Beeline

🔹 **Описание**
Модуль обеспечивает взаимодействие с API Beeline для автоматизации процессов, связанных с телекоммуникационными услугами (SMS-рассылки, управление номерами, биллинг и т. д.).  

🔹 **Функционал**
- Отправка SMS через Beeline API
- Проверка статуса доставки сообщений
- Управление балансом и тарифами
- Логирование запросов и ошибок

---

## 📌 Установка и настройка

1. **Клонируйте репозиторий**
    ```bash
    sudo mkdir /opt/beeline_module/
    cd /opt/beeline_module/
    git clone https://github.com/SibayMaktay/beeline_module.git .

2. **Создание окружения**
    ```bash
    python3 -m venv .venv

3. **Активация окружения**
    ```bash
    source .venv/bin/activate

4. **Установите зависимости**
    ```bash
    pip install -r requirements.txt

5. **Запуск приложения**
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 9090

6. **Настройте конфигурацию**
    скопируйте или измените файл из ./config/.env.default на ./config/.env
    внутри файла измените:
    ```.env
    BEELINE_LOGIN= # login
    BEELINE_PASSWORD= # password
    BEELINE_URL_BASE=https://my.beeline.ru
    BEELINE_REST_SIGNATURE= # secret signature
    
    UTM5_URL_BASE= # url base
    UTM5_API_URL= # api url http://127.0.0.1:9080
    UTM5_LOGIN= # login
    UTM5_PASSWORD= # password
    UTM5_API_KEY= # api key utm5

    MODULE_API_KEY=bee_test # api key module beeline
    MODULE_ADMIN_API_KEY=bee_test_admin # admin api key modyule beeline