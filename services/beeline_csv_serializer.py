from typing import Dict, List

BEELINE_ORDER_MAPPING = [
    ("Гражданство", "citizenship"),
    ("Номер документа", "docNo"),
    ("Тип документа", "docType"),
    ("Дата выдачи", "docIssueDate"),
    ("Кем выдан", "docIssuer"),
    ("Код подразделения выдавшего документ", "docIssuerCode"),
    ("Документ действителен до", "docExpirationDate"),
    ("Дата рождения", "birthdate"),
    ("Номер миграционной карты", "frnMigcard"),
    ("Дата выдачи миграционной карты", "frnMigcardEffDate"),
    ("Срок действия миграционной карты", "frnMigcardExpDate"),
    ("Документ нерезидента", "frnDoc"),
    ("Имя", "firstName"),
    ("Отчество", "surName"),
    ("Фамилия", "lastName"),
    ("Место рождения", "birthplace"),
    ("Пол", "gender"),
    ("ИНН", "taxNumber"),
    ("СНИЛС", "snils"),
    ("АдрРег Индекс", "legalPostcode"),
    ("АдрРег Код страны", "legalCountryCode"),
    ("АдрРег Регион", "legalRegion"),
    ("АдрРег Район", "legalArea"),
    ("АдрРег Тип НП", "legalPlaceType"),
    ("АдрРег Населенный пункт", "legalPlace"),
    ("АдрРег Тип улицы", "legalStreetType"),
    ("АдрРег Улица", "legalStreetName"),
    ("АдрРег Тип дома", "legalHouseType"),
    ("АдрРег Номер дома", "legalHouseNo"),
    ("АдрРег Тип строения", "legalBuildingType"),
    ("АдрРег Номер строения", "legalBuildingNo"),
    ("АдрРег Тип помещения", "legalApartmentType"),
    ("АдрРег Номер помещения", "legalApartmentNo"),
    ("АдрРег Комментарий", "legalAddrComment"),
    ("АдрРег ФИАС ИД", "legalFiasId"),
    ("АдрПрож Индекс", "actualPostcode"),
    ("АдрПрож Код страны", "actualCountryCode"),
    ("АдрПрож Регион", "actualRegion"),
    ("АдрПрож Район", "actualArea"),
    ("АдрПрож Тип НП", "actualPlaceType"),
    ("АдрПрож Населенный пункт", "actualPlace"),
    ("АдрПрож Тип улицы", "actualStreetType"),
    ("АдрПрож Улица", "actualStreetName"),
    ("АдрПрож Тип дома", "actualHouseType"),
    ("АдрПрож Номер дома", "actualHouseNo"),
    ("АдрПрож Тип строения", "actualBuildingType"),
    ("АдрПрож Номер строения", "actualBuildingNo"),
    ("АдрПрож Тип помещения", "actualApartmentType"),
    ("АдрПрож Номер помещения", "actualApartmentNo"),
    ("АдрПрож Комментарий", "actualAddrComment"),
    ("АдрПрож ФИАС ИД", "actualFiasId"),
]

def serialize_personal_data_for_beeline_multi_ctn(data: Dict) -> str:
    """
    Сериализует данные для Beeline: для ctn = '1,2,3' вернёт 3 строки по формату 'ban;ctn;...'
    """
    ctn_raw = data.get('ctn', '')
    ban = data.get('ban', '')

    ctn_list = [item.strip() for item in ctn_raw.split(',') if item.strip()]

    postfix = []
    for _, model_field in BEELINE_ORDER_MAPPING:
        val = data.get(model_field)
        postfix.append("" if val is None else str(val))
    postfix_str = ";".join(postfix)

    rows = []
    for ctn in ctn_list:
        row = f"{ban};{ctn};{postfix_str};"
        rows.append(row)
    return """
    """.join(rows)