from templates.wsdl_template_beeline import *

# Max method parametrs

print(
    restore_ctn_template(
        ctn="7000333", reason_code="REAS-77", session_id="ABCD-1234", login="QWERTY", actv_date="2024-07-01"
    ),
    suspend_ctn_template(
        ctn="7000333", reason_code="REAS-77", session_id="ABCD-1234", login="QWERTY", actv_date="2024-07-01"
    ),
    replace_sim_template(
        ctn="7000333", serial_number="SN-987654", session_id="ABCD-1234", login="QWERTY"
    ),
    get_details_template(
        session_id="ABCD-1234", request_id="REQ-0001", login="QWERTY"
    ),
    get_request_list_template(
        session_id="ABCD-1234", page=1, login="QWERTY", start_date="2024-06-01", end_date="2024-06-30", request_id="REQ-0001", records_per_page="50"
    ),
    get_bill_calls_template(
        session_id="ABCD-1234", request_id="REQ-0001", login="QWERTY"
    ),
    get_adjustment_list_template(
        session_id="ABCD-1234", ban="9000666", start_date="2024-06-01", end_date="2024-06-30", login="QWERTY"
    ),
    get_bill_charges_template(
        session_id="ABCD-1234", request_id="REQ-0001", login="QWERTY"
    ),
    get_bill_charges_paged_template(
        session_id="ABCD-1234", request_id="REQ-0001", page=1, login="QWERTY", records_per_page="50"
    ),
    get_ctn_info_list_template(
        ban="9000666", session_id="ABCD-1234", ctn="7000333", login="QWERTY"
    ),
    get_ctn_info_list_paged_template(
        ban="9000666", session_id="ABCD-1234", page=1, login="QWERTY", ctn="7000333", records_per_page="50"
    ),
    get_payment_list_template(
        ban="9000666", start_date="2024-06-01", end_date="2024-06-30", session_id="ABCD-1234", ctn="7000333", login="QWERTY"
    ),
    get_payment_list_paged_template(
        ban="9000666", start_date="2024-06-01", end_date="2024-06-30", session_id="ABCD-1234", page=1, ctn="7000333", login="QWERTY", records_per_page="50"
    ),
    get_sim_list_template(
        session_id="ABCD-1234", ban="9000666", ctn="7000333", login="QWERTY"
    ),
    get_sim_list_paged_template(
        session_id="ABCD-1234", ban="9000666", page=1, ctn="7000333", login="QWERTY", records_per_page="50"
    ),
    get_services_list_template(
        session_id="ABCD-1234", ban="9000666", ctn="7000333", login="QWERTY"
    ),
    get_services_list_paged_template(
        session_id="ABCD-1234", ban="9000666", page=1, ctn="7000333", login="QWERTY", ctn_amount_per_page="10"
    ),
    get_unbilled_balance_template(
        ctn="7000333", session_id="ABCD-1234", login="QWERTY"
    ),
    get_unbilled_calls_list_template(
        session_id="ABCD-1234", ctn="7000333", login="QWERTY"
    ),
    add_shared_number_list_dol_template(
        session_id="ABCD-1234", ctn_from="7000999", ctn_to_list="<num>7000888</num>", ctn_to="7000245", soc="SOC-912", prepaid_state_chk_cancel="N", check_add_number_registration="Y"
    ),
    delete_shared_number_list_dol_template(
        session_id="ABCD-1234", ctn_from="7000999", ctn_to_list="<num>7000888</num>", ctn_to="7000245"
    ),
    personal_data_update_template(
        session_id="ABCD-1234", data="<Data><type>update</type></Data>", login="QWERTY"
    ),
    personal_data_result_template(
        session_id="ABCD-1234", request_id="REQ-0001", login="QWERTY"
    ),
    get_data_report_template(
        session_id="ABCD-1234", request_id="REQ-0001", page=1, login="QWERTY", records_per_page="50"
    ),
    add_del_soc_template(
        ctn="7000333", soc="SOC-912", inclusion_type="add", session_id="ABCD-1234", eff_date="2024-07-01", exp_date="2024-12-31", login="QWERTY"
    ),
    change_pp_template(
        ctn="7000333", pricePlan="NEWPLAN", session_id="ABCD-1234", futureDate="2024-08-01", login="QWERTY", freeChange="true"
    ),
    get_ban_info_list_template(
        session_id="ABCD-1234", login="QWERTY"
    ),
    add_shared_number_dol_template(
        session_id="ABCD-1234", request_id="REQ-0001", ctn_to="7000245", ctn_type="type1", soc="SOC-912", prepaid_state_chk_cancel="N", check_add_number_registration="Y"
    ),
    create_bill_calls_request_template(
        session_id="ABCD-1234", ban="9000666", bill_date="2024-06-01", login="QWERTY", ctn_list="<num>7000111</num><num>7000222</num>"
    ),
    create_bill_charges_request_template(
        session_id="ABCD-1234", ban="9000666", bill_date="2024-06-01", login="QWERTY", ctn_list="<num>7000111</num><num>7000222</num>"
    ),
    create_details_request_template(
        session_id="ABCD-1234", ctn="7000333", period_start="2024-06-01", period_end="2024-06-30", format_="pdf", login="QWERTY", channel="email", email="user@example.com"
    ),
    get_ban_info_list_paged_template(
        session_id="ABCD-1234", login="QWERTY", page=1, records_per_page="50"
    ),
    get_bill_calls_paged_template(
        session_id="ABCD-1234", request_id="REQ-0001", page=1, login="QWERTY", records_per_page="50"
    ),
    get_data_template(
        session_id="ABCD-1234", login="QWERTY", ban="9000666", hierarchy_id="HIER-91", subscriber_no="SUBSCR-49"
    ),
    sep="\n\n"  # Чтобы видеть каждый XML шаблон отдельно
)

# Min method parametrs

# print(
#     get_auth_template(
#         login="QWERTY",
#         password="12345678"
#     ),
#     restore_ctn_template(
#         ctn="7000333", reason_code="REAS-77", session_id="ABCD-1234"
#     ),
#     suspend_ctn_template(
#         ctn="7000333", reason_code="REAS-77", session_id="ABCD-1234"
#     ),
#     replace_sim_template(
#         ctn="7000333", serial_number="SN-987654", session_id="ABCD-1234"
#     ),
#     get_details_template(
#         session_id="ABCD-1234", request_id="REQ-0001"
#     ),
#     get_request_list_template(
#         session_id="ABCD-1234"
#     ),
#     get_bill_calls_template(
#         session_id="ABCD-1234", request_id="REQ-0001"
#     ),
#     get_adjustment_list_template(
#         session_id="ABCD-1234", ban="9000666", start_date="2024-06-01", end_date="2024-06-30"
#     ),
#     get_bill_charges_template(
#         session_id="ABCD-1234", request_id="REQ-0001"
#     ),
#     get_bill_charges_paged_template(
#         session_id="ABCD-1234", request_id="REQ-0001", page=1
#     ),
#     get_ctn_info_list_template(
#         ban="9000666", session_id="ABCD-1234"
#     ),
#     get_ctn_info_list_paged_template(
#         ban="9000666", session_id="ABCD-1234"
#     ),
#     get_payment_list_template(
#         ban="9000666", start_date="2024-06-01", end_date="2024-06-30", session_id="ABCD-1234"
#     ),
#     get_payment_list_paged_template(
#         ban="9000666", start_date="2024-06-01", end_date="2024-06-30", session_id="ABCD-1234"
#     ),
#     get_sim_list_template(
#         session_id="ABCD-1234", ban="9000666"
#     ),
#     get_sim_list_paged_template(
#         session_id="ABCD-1234", ban="9000666"
#     ),
#     get_services_list_template(
#         session_id="ABCD-1234", ban="9000666"
#     ),
#     get_services_list_paged_template(
#         session_id="ABCD-1234", ban="9000666"
#     ),
#     get_unbilled_balance_template(
#         ctn="7000333", session_id="ABCD-1234", login="QWERTY"
#     ),
#     get_unbilled_calls_list_template(
#         session_id="ABCD-1234", ctn="7000333"
#     ),
#     add_shared_number_list_dol_template(
#         session_id="ABCD-1234", ctn_from="7000999", ctn_to_list="<num>7000888</num>", ctn_to="7000245"
#     ),
#     delete_shared_number_list_dol_template(
#         session_id="ABCD-1234", ctn_from="7000999", ctn_to_list="<num>7000888</num>", ctn_to="7000245"
#     ),
#     personal_data_update_template(
#         session_id="ABCD-1234", data="<Data><type>update</type></Data>"
#     ),
#     personal_data_result_template(
#         session_id="ABCD-1234", request_id="REQ-0001"
#     ),
#     get_data_report_template(
#         session_id="ABCD-1234", request_id="REQ-0001"
#     ),
#     add_del_soc_template(
#         ctn="7000333", soc="SOC-912", inclusion_type="add", session_id="ABCD-1234"
#     ),
#     change_pp_template(
#         ctn="7000333", price_plan="NEWPLAN", session_id="ABCD-1234", free_change="true"
#     ),
#     get_ban_info_list_template(
#         session_id="ABCD-1234", login="QWERTY"
#     ),
#     add_shared_number_dol_template(
#         session_id="ABCD-1234", request_id="REQ-0001", ctn_to="7000245", ctn_type="type1", soc="SOC-912", prepaid_state_chk_cancel="N", check_add_number_registration="Y"
#     ),
#     create_bill_calls_request_template(
#         session_id="ABCD-1234", ban="9000666", bill_date="2024-06-01"
#     ),
#     create_bill_charges_request_template(
#         session_id="ABCD-1234", ban="9000666", bill_date="2024-06-01"
#     ),
#     create_details_request_template(
#         session_id="ABCD-1234", ctn="7000333", period_start="2024-06-01", period_end="2024-06-30", format_="pdf"
#     ),
#     get_ban_info_list_paged_template(
#         session_id="ABCD-1234", login="QWERTY"
#     ),
#     get_bill_calls_paged_template(
#         session_id="ABCD-1234", request_id="REQ-0001"
#     ),
#     get_data_template(
#         session_id="ABCD-1234", login="QWERTY", ban="9000666", hierarchy_id="HIER-91", subscriber_no="SUBSCR-49"
#     ),
#     sep="\n\n"  # Чтобы видеть каждый XML шаблон отдельно
# )