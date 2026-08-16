import requests

class UTM5RestClient:
    def __init__(self, base_url, api_key):
        """
        base_url: e.g., "https://your-utm5-host/api"
        api_key: токен от UTM5 (X-Api-Auth)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Auth': self.api_key,
            'Content-Type': 'application/json'
        })

    def get_users(self):
        """Получить список всех пользователей"""
        url = f"{self.base_url}/user"
        r = self.session.get(url)
        r.raise_for_status()
        return r.json()['items']

    def search_user_by_query(self, query):
        """
        Поиск пользователей (по номеру телефона, логину, ФИО и т.д.)
        """
        url = f"{self.base_url}/user/search"
        r = self.session.post(url, json={"query": query})
        r.raise_for_status()
        return r.json()["items"]  # всегда список

    def get_user(self, user_id):
        """Получить пользователя по ID"""
        url = f"{self.base_url}/user/{user_id}"
        r = self.session.get(url)
        r.raise_for_status()
        return r.json()

    def create_user(self, login, password, full_name, phone=None):
        """Создать нового пользователя"""
        data = {
            "basic_data": {
                "login": login,
                "password": password,
                "full_name": full_name,
            },
            "contacts_data": {
                "mobile_phone": phone
            } if phone else {},
            "account": {"create": True}
        }
        url = f"{self.base_url}/user"
        r = self.session.post(url, json=data)
        r.raise_for_status()
        return r.json()

    def pay_user(self, user_id, amount, comment="payment"):
        url = f"{self.base_url}/user/{user_id}/pay"
        r = self.session.post(url, json={"amount": float(amount), "comment": comment})
        r.raise_for_status()
        return r.json()

    def get_tariffs(self):
        """Получить список всех тарифов"""
        url = f"{self.base_url}/tariff"
        r = self.session.get(url)
        r.raise_for_status()
        return r.json()['items']

    def set_user_tariff(self, user_id, tariff_id):
        """Сменить пользователю тариф"""
        url = f"{self.base_url}/user/{user_id}/tariff"
        r = self.session.post(url, json={"tariff_id": tariff_id})
        r.raise_for_status()
        return r.json()

    def get_user_services(self, user_id):
        """Получить услуги пользователя (например, текущие IP/интернет/телефония)"""
        url = f"{self.base_url}/user/{user_id}/service"
        r = self.session.get(url)
        r.raise_for_status()
        return r.json()['items']